import {
  Alert, AlertIcon, Badge, Box, Button, Collapse, FormControl, FormHelperText, FormLabel,
  HStack, Icon, Input, Select, SimpleGrid, Text, Tooltip, VStack, useToast,
} from "@chakra-ui/react";
import { ArrowsRightLeftIcon, ChevronDownIcon, ChevronUpIcon, InformationCircleIcon } from "@heroicons/react/24/outline";
import { FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { generateErrorMessage } from "utils/toastHandler";

type Relay = {
  configured: boolean; mode: "direct" | "relay"; source: "main";
  entry_address: string | null; allocation: "auto" | "manual"; listen_port: number | null;
  inbound_tag: string | null; target_address: string | null; target_port: number | null;
  status: "inactive" | "pending" | "running" | "error"; error: string | null;
};
type Options = {
  default_entry_address: string;
  inbounds: { tag: string; port: number; protocol: string; network: string; tls: string }[];
};
type Form = { mode: "direct" | "relay"; entry: string; allocation: "auto" | "manual"; port: string; inbound: string };

export const NodeRelayCard: FC<{ nodeId: number; nodeName: string; address: string; disabled?: boolean }> = ({ nodeId, nodeName, address, disabled }) => {
  const { t } = useTranslation();
  const toast = useToast();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [form, setForm] = useState<Form>({ mode: "direct", entry: "", allocation: "auto", port: "", inbound: "" });
  const key = ["node-relay", nodeId];
  const query = useQuery<Relay>(key, () => fetch(`/node/${nodeId}/relay`), { retry: false, refetchInterval: open ? 15000 : false });
  const options = useQuery<Options>("node-relay-options", () => fetch("/nodes/relay/options"), { enabled: open, retry: false });
  useEffect(() => {
    if (dirty || !query.data) return;
    const value = query.data;
    setForm({ mode: value.mode, entry: value.entry_address || options.data?.default_entry_address || "",
      allocation: value.allocation || "auto", port: String(value.listen_port || ""),
      inbound: value.inbound_tag || options.data?.inbounds[0]?.tag || "" });
  }, [query.data, options.data, dirty]);
  const update = (values: Partial<Form>) => { setDirty(true); setForm(current => ({ ...current, ...values })); };
  const save = useMutation(() => fetch<Relay>(`/node/${nodeId}/relay`, {
    method: "PUT", body: form.mode === "direct" ? { mode: "direct" } : {
      mode: "relay", source: "main", entry_address: form.entry.trim(), allocation: form.allocation,
      listen_port: form.allocation === "manual" ? Number(form.port) : null, inbound_tag: form.inbound,
    },
  }), {
    onSuccess: result => {
      client.setQueryData(key, result);
      client.invalidateQueries("node-relay-options");
      setDirty(false);
      toast({ status: "success", title: t("nodes.relay.saved") });
    }, onError: error => { generateErrorMessage(error, toast); },
  });
  const target = options.data?.inbounds.find(item => item.tag === form.inbound);
  const portValid = form.allocation === "auto" || (/^\d+$/.test(form.port) && Number(form.port) >= 1024 && Number(form.port) <= 65535);
  const automaticPort = String(query.data?.listen_port || "");
  const displayedPort = form.allocation === "auto" ? automaticPort : form.port;
  const canSave = !query.isError && !query.isLoading && (form.mode === "direct" || (!options.isError && !disabled && !!form.entry.trim() && !!target && portValid));
  const entryPort = displayedPort || t("nodes.relay.allocatedOnSave");
  return <Box w="full" mt={3} borderWidth="1px" borderColor="gray.200" _dark={{ borderColor: "gray.600" }} borderRadius="md">
    <Button type="button" variant="ghost" w="full" h="auto" py={2} px={3} justifyContent="space-between"
      onClick={() => setOpen(!open)} aria-expanded={open} aria-controls={`relay-body-${nodeId}`}>
      <HStack spacing={2} minW={0} flexWrap="wrap">
        <Icon as={ArrowsRightLeftIcon} boxSize="18px" />
        <Text fontSize="sm" fontWeight="medium">{t("nodes.relay.title")}</Text>
        <Text fontSize="xs" color="gray.500" fontWeight="normal">{t(query.data?.configured ? "nodes.relay.viaMain" : "nodes.relay.direct")}</Text>
      </HStack>
      <Icon as={open ? ChevronUpIcon : ChevronDownIcon} boxSize="16px" flexShrink={0} />
    </Button>
    <Collapse in={open} animateOpacity>
      <VStack id={`relay-body-${nodeId}`} align="stretch" spacing={3} px={3} pb={3}>
        {(query.isError || options.isError) && <Alert status="error"><AlertIcon /><Box flex={1} minW={0}><Text fontSize="xs">{t("nodes.relay.loadFailed")}</Text></Box><Button size="xs" type="button" onClick={() => { query.refetch(); options.refetch(); }}>{t("nodes.relay.retry")}</Button></Alert>}
        <FormControl>
          <FormLabel display="flex" alignItems="center" gap={2}>{t("nodes.relay.mode")}
            <Tooltip hasArrow label={t("nodes.relay.modeHelp")}>
              <Box as="span" display="inline-flex" tabIndex={0} aria-label={t("nodes.relay.modeHelp")}><Icon as={InformationCircleIcon} boxSize="16px" color="gray.500" /></Box>
            </Tooltip>
          </FormLabel>
          <Select size="sm" value={form.mode} isDisabled={save.isLoading} onChange={event => update({ mode: event.target.value as Form["mode"] })}>
            <option value="direct">{t("nodes.relay.direct")}</option><option value="relay">{t("nodes.relay.relay")}</option>
          </Select>
        </FormControl>
        {form.mode === "relay" && <>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
            <FormControl><FormLabel>{t("nodes.relay.server")}</FormLabel><Select size="sm" value="main" isDisabled><option value="main">{t("nodes.relay.mainServer")}</option></Select></FormControl>
            <FormControl isRequired><FormLabel>{t("nodes.relay.entryAddress")}</FormLabel><Input size="sm" value={form.entry} placeholder="hk01.example.com" isDisabled={save.isLoading} onChange={event => update({ entry: event.target.value })} /><FormHelperText>{t("nodes.relay.addressHelp")}</FormHelperText></FormControl>
            <FormControl isInvalid={!portValid}><FormLabel>{t("nodes.relay.entryPort")}</FormLabel><HStack spacing={2}>
              <Select size="sm" w="106px" flexShrink={0} value={form.allocation} isDisabled={save.isLoading} aria-label={t("nodes.relay.allocation")} onChange={event => update({ allocation: event.target.value as Form["allocation"] })}>
                <option value="auto">{t("nodes.relay.auto")}</option><option value="manual">{t("nodes.relay.manual")}</option>
              </Select><Input size="sm" minW={0} type="number" min={1024} max={65535} value={displayedPort} placeholder="18443" isReadOnly={form.allocation === "auto"} isDisabled={save.isLoading} aria-label={t("nodes.relay.entryPort")} onChange={event => update({ port: event.target.value })} />
            </HStack><FormHelperText>{t(portValid ? "nodes.relay.portHelp" : "nodes.relay.invalidPort")}</FormHelperText></FormControl>
            <FormControl isRequired><FormLabel>{t("nodes.relay.targetInbound")}</FormLabel><Select size="sm" value={form.inbound} isDisabled={save.isLoading || options.isLoading} onChange={event => update({ inbound: event.target.value })}>
              <option value="" disabled>{t("nodes.relay.selectInbound")}</option>
              {options.data?.inbounds.map(item => <option key={item.tag} value={item.tag}>{item.tag} · {item.port}</option>)}
            </Select><FormHelperText>{t("nodes.relay.targetHelp")}</FormHelperText></FormControl>
          </SimpleGrid>
          {options.data && !options.data.inbounds.length && <Text color="red.500" fontSize="xs">{t("nodes.relay.noInbound")}</Text>}
        </>}
        <Box borderRadius="md" bg="gray.50" _dark={{ bg: "gray.750" }} p={3}>
          <HStack justify="space-between" flexWrap="wrap" gap={1} mb={2}><Text fontSize="xs" fontWeight="medium">{t("nodes.relay.subscriptionPreview")}</Text>
            <Badge fontSize="10px" colorScheme={query.data?.status === "running" && !dirty ? "green" : "gray"}>{t(dirty ? "nodes.relay.unsaved" : `nodes.relay.status.${query.data?.status || "pending"}`)}</Badge>
          </HStack>
          <Text fontSize="sm" fontWeight="medium" overflowWrap="anywhere">{nodeName}{form.mode === "relay" ? " (Relay)" : ""}</Text>
          <Text fontSize="xs" color="gray.500" mt={1} overflowWrap="anywhere">{form.mode === "relay" ? `${form.entry || "—"}:${entryPort} → ${address}:${target?.port || query.data?.target_port || "—"}` : address}</Text>
          <Text fontSize="xs" mt={2}>{t(form.mode === "relay" ? "nodes.relay.exitHelp" : "nodes.relay.directHelp")}</Text>
        </Box>
        {query.data?.error && <Text fontSize="xs" color="red.500" overflowWrap="anywhere">{query.data.error}</Text>}
        <Text fontSize="xs" color="gray.500">{t("nodes.relay.preserved")}</Text>
        <Text fontSize="xs" color="gray.500">{t("nodes.relay.applyHelp")}</Text>
        <Button type="button" size="sm" colorScheme="primary" isLoading={save.isLoading} isDisabled={!canSave || !dirty} onClick={() => save.mutate()}>{t("nodes.relay.save")}</Button>
      </VStack>
    </Collapse>
  </Box>;
};
