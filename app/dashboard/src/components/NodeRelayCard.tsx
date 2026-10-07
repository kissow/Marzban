import {
  Alert, AlertIcon, Badge, Box, Button, FormControl, FormErrorMessage, FormLabel,
  HStack, Icon, IconButton, Input, Modal, ModalBody, ModalCloseButton, ModalContent,
  ModalFooter, ModalHeader, ModalOverlay, Select, SimpleGrid, Text, Tooltip, VStack,
  useDisclosure, useToast,
} from "@chakra-ui/react";
import { ArrowsRightLeftIcon, InformationCircleIcon } from "@heroicons/react/24/outline";
import { FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { generateErrorMessage } from "utils/toastHandler";

type Relay = {
  configured: boolean; mode: "direct" | "relay"; source: "main" | "node"; source_node_id: number | null;
  entry_address: string | null; allocation: "auto" | "manual"; listen_port: number | null;
  inbound_tag: string | null; target_address: string | null; target_port: number | null;
  status: "inactive" | "pending" | "running" | "error"; error: string | null;
};
type Options = {
  default_entry_address: string;
  source_nodes: { id: number; name: string; address: string; connected: boolean }[];
  inbounds: { tag: string; port: number; protocol: string; network: string; tls: string }[];
};
type Form = { mode: "direct" | "relay"; source: "main" | "node"; sourceId: string; entry: string; allocation: "auto" | "manual"; port: string; inbound: string };

// Same information-circle asset/theme as the original Hosts dialog. Controlled
// visibility also supports tapping on touchscreens and focus/Escape on keyboards.
const RelayHelp: FC<{ label: string; help: string }> = ({ label, help }) => {
  const [visible, setVisible] = useState(false);
  const [pinned, setPinned] = useState(false);
  return <Tooltip label={help} hasArrow placement="top" isOpen={visible}
    maxW="min(320px, calc(100vw - 32px))" whiteSpace="normal" overflowWrap="anywhere">
    <IconButton type="button" aria-label={label} aria-expanded={visible} variant="unstyled"
      display="inline-flex" alignItems="center" justifyContent="center" minW="24px" h="24px"
      color="gray.400" icon={<Icon as={InformationCircleIcon} boxSize={4} />}
      onMouseEnter={() => setVisible(true)} onMouseLeave={() => { if (!pinned) setVisible(false); }}
      onFocus={() => setVisible(true)} onBlur={() => { setPinned(false); setVisible(false); }}
      onClick={() => { setPinned(!pinned); setVisible(!pinned); }}
      onKeyDown={event => { if (event.key === "Escape" && visible) { event.stopPropagation(); setPinned(false); setVisible(false); } }} />
  </Tooltip>;
};

export const NodeRelayCard: FC<{ nodeId: number; nodeName: string; address: string; disabled?: boolean }> = ({ nodeId, nodeName, address, disabled }) => {
  const { t } = useTranslation();
  const toast = useToast();
  const client = useQueryClient();
  const modal = useDisclosure();
  const [dirty, setDirty] = useState(false);
  const [form, setForm] = useState<Form>({ mode: "direct", source: "main", sourceId: "", entry: "", allocation: "auto", port: "", inbound: "" });
  const key = ["node-relay", nodeId];
  const query = useQuery<Relay>(key, () => fetch(`/node/${nodeId}/relay`), { retry: false, refetchInterval: modal.isOpen ? 15000 : false });
  const options = useQuery<Options>("node-relay-options", () => fetch("/nodes/relay/options"), { enabled: modal.isOpen, retry: false });
  useEffect(() => {
    if (dirty || !query.data) return;
    const value = query.data;
    setForm({ mode: value.mode, source: value.source || "main", sourceId: String(value.source_node_id || ""), entry: value.entry_address || options.data?.default_entry_address || "",
      allocation: value.allocation || "auto", port: String(value.listen_port || ""),
      inbound: value.inbound_tag || options.data?.inbounds[0]?.tag || "" });
  }, [query.data, options.data, dirty]);
  const update = (values: Partial<Form>) => { setDirty(true); setForm(current => ({ ...current, ...values })); };
  const save = useMutation(() => fetch<Relay>(`/node/${nodeId}/relay`, {
    method: "PUT", body: form.mode === "direct" ? { mode: "direct" } : {
      mode: "relay", source: form.source, source_node_id: form.source === "node" ? Number(form.sourceId) : null, entry_address: form.entry.trim(), allocation: form.allocation,
      listen_port: form.allocation === "manual" ? Number(form.port) : null, inbound_tag: form.inbound,
    },
  }), {
    onSuccess: result => {
      client.setQueryData(key, result);
      client.invalidateQueries("node-relay-options");
      setDirty(false);
      modal.onClose();
      toast({ status: "success", title: t("nodes.relay.saved") });
    }, onError: error => { generateErrorMessage(error, toast); },
  });
  const target = options.data?.inbounds.find(item => item.tag === form.inbound);
  const portValid = form.allocation === "auto" || (/^\d+$/.test(form.port) && Number(form.port) >= 1024 && Number(form.port) <= 65535);
  const sourceNodes = options.data?.source_nodes?.filter(item => item.id !== nodeId && item.address.toLowerCase() !== address.toLowerCase()) || [];
  const sourceValid = form.source === "main" || sourceNodes.some(item => String(item.id) === form.sourceId && item.connected);
  const automaticPort = query.data?.source === form.source && String(query.data?.source_node_id || "") === form.sourceId ? String(query.data?.listen_port || "") : "";
  const displayedPort = form.allocation === "auto" ? automaticPort : form.port;
  const canSave = !query.isError && !query.isLoading && (form.mode === "direct" || (!options.isError && !disabled && sourceValid && !!form.entry.trim() && !!target && portValid));
  const chooseSource = (value: string) => {
    const sourceId = value.startsWith("node:") ? value.slice(5) : "";
    update({ source: sourceId ? "node" : "main", sourceId,
      entry: sourceId ? sourceNodes.find(item => String(item.id) === sourceId)?.address || "" : options.data?.default_entry_address || "" });
  };
  const entryPort = displayedPort || t("nodes.relay.allocatedOnSave");
  const openManager = () => { setDirty(false); save.reset(); modal.onOpen(); query.refetch(); };
  const closeManager = () => { if (!save.isLoading) { modal.onClose(); setDirty(false); } };
  return <>
    <HStack w="full" minH="38px" justify="space-between" borderWidth="1px"
      borderColor="gray.200" _dark={{ borderColor: "gray.600" }} borderRadius="md" px={3} py={2}>
      <HStack spacing={2} minW={0}>
        <Icon as={ArrowsRightLeftIcon} boxSize="18px" />
        <Text fontSize="sm" fontWeight="medium" noOfLines={1}>{t("nodes.relay.title")}</Text>
        <Text fontSize="xs" color="gray.500" flexShrink={0} display={{ base: "none", sm: "block" }}>{t(query.data?.configured ? query.data.source === "node" ? "nodes.relay.viaNode" : "nodes.relay.viaMain" : "nodes.relay.direct")}</Text>
      </HStack>
      <Button type="button" size="xs" variant="outline" colorScheme="primary" onClick={openManager}
        flexShrink={0}>{t("nodes.relay.manage")}</Button>
    </HStack>
    <Modal isOpen={modal.isOpen} onClose={closeManager} size="lg" isCentered scrollBehavior="inside"
      closeOnEsc={!save.isLoading} closeOnOverlayClick={!save.isLoading}>
      <ModalOverlay />
      <ModalContent mx={3} maxW={{ base: "calc(100vw - 24px)", md: "lg" }}>
        <ModalHeader fontSize="md" pr={12} overflowWrap="anywhere">{nodeName} · {t("nodes.relay.title")}</ModalHeader>
        <ModalCloseButton isDisabled={save.isLoading} />
        <ModalBody pt={0}>
      <VStack align="stretch" spacing={3}>
        {(query.isError || options.isError) && <Alert status="error"><AlertIcon /><Box flex={1} minW={0}><Text fontSize="xs">{t("nodes.relay.loadFailed")}</Text></Box><Button size="xs" type="button" onClick={() => { query.refetch(); options.refetch(); }}>{t("nodes.relay.retry")}</Button></Alert>}
        <FormControl>
          <FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>{t("nodes.relay.mode")}
            <RelayHelp label={t("nodes.relay.mode")} help={t("nodes.relay.modeHelp")} />
          </FormLabel>
          <Select size="sm" value={form.mode} isDisabled={save.isLoading} onChange={event => update({ mode: event.target.value as Form["mode"] })}>
            <option value="direct">{t("nodes.relay.direct")}</option><option value="relay">{t("nodes.relay.relay")}</option>
          </Select>
        </FormControl>
        {form.mode === "relay" && <>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
            <FormControl><FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>{t("nodes.relay.server")}<RelayHelp label={t("nodes.relay.server")} help={t("nodes.relay.serverHelp")} /></FormLabel><Select size="sm" value={form.source === "main" ? "main" : `node:${form.sourceId}`} isDisabled={save.isLoading || options.isLoading} onChange={event => chooseSource(event.target.value)}>
              <option value="main">{t("nodes.relay.mainServer")}</option>
              {form.source === "node" && !sourceNodes.some(item => String(item.id) === form.sourceId) && <option value={`node:${form.sourceId}`} disabled>{t("nodes.relay.selectSource")}</option>}
              {sourceNodes.map(item => <option key={item.id} value={`node:${item.id}`} disabled={!item.connected}>{item.name}</option>)}
            </Select></FormControl>
            <FormControl isRequired><FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>{t("nodes.relay.entryAddress")}<RelayHelp label={t("nodes.relay.entryAddress")} help={t("nodes.relay.addressHelp")} /></FormLabel><Input size="sm" value={form.entry} placeholder="main.example.com" isDisabled={save.isLoading} onChange={event => update({ entry: event.target.value })} /></FormControl>
            <FormControl isInvalid={!portValid}><FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>{t("nodes.relay.entryPort")}<RelayHelp label={t("nodes.relay.entryPort")} help={t("nodes.relay.portHelp")} /></FormLabel><HStack spacing={2}>
              <Select size="sm" w="106px" flexShrink={0} value={form.allocation} isDisabled={save.isLoading} aria-label={t("nodes.relay.allocation")} onChange={event => update({ allocation: event.target.value as Form["allocation"] })}>
                <option value="auto">{t("nodes.relay.auto")}</option><option value="manual">{t("nodes.relay.manual")}</option>
              </Select><Input size="sm" minW={0} type="number" min={1024} max={65535} value={displayedPort} placeholder="18443" isReadOnly={form.allocation === "auto"} isDisabled={save.isLoading} aria-label={t("nodes.relay.entryPort")} onChange={event => update({ port: event.target.value })} />
            </HStack><FormErrorMessage>{t("nodes.relay.invalidPort")}</FormErrorMessage></FormControl>
            <FormControl isRequired><FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>{t("nodes.relay.targetInbound")}<RelayHelp label={t("nodes.relay.targetInbound")} help={t("nodes.relay.targetHelp")} /></FormLabel><Select size="sm" value={form.inbound} isDisabled={save.isLoading || options.isLoading} onChange={event => update({ inbound: event.target.value })}>
              <option value="" disabled>{t("nodes.relay.selectInbound")}</option>
              {options.data?.inbounds.map(item => <option key={item.tag} value={item.tag}>{item.tag} · {item.port}</option>)}
            </Select></FormControl>
          </SimpleGrid>
          {options.data && !options.data.inbounds.length && <Text color="red.500" fontSize="xs">{t("nodes.relay.noInbound")}</Text>}
        </>}
        <Box borderRadius="md" bg="gray.50" _dark={{ bg: "gray.750" }} p={3}>
          <HStack justify="space-between" flexWrap="wrap" gap={1} mb={2}><HStack spacing={1}><Text fontSize="xs" fontWeight="medium">{t("nodes.relay.subscriptionPreview")}</Text><RelayHelp label={t("nodes.relay.subscriptionPreview")} help={`${t(form.mode === "relay" ? "nodes.relay.exitHelp" : "nodes.relay.directHelp")} ${t("nodes.relay.preserved")}`} /></HStack>
            <Badge fontSize="10px" colorScheme={query.data?.status === "running" && !dirty ? "green" : "gray"}>{t(dirty ? "nodes.relay.unsaved" : `nodes.relay.status.${query.data?.status || "pending"}`)}</Badge>
          </HStack>
          <Text fontSize="sm" fontWeight="medium" overflowWrap="anywhere">{nodeName}</Text>
          <Text fontSize="xs" color="gray.500" mt={1} overflowWrap="anywhere">{form.mode === "relay" ? `${form.entry || "—"}:${entryPort} → ${address}:${target?.port || query.data?.target_port || "—"}` : address}</Text>
        </Box>
        {query.data?.error && <Text fontSize="xs" color="red.500" overflowWrap="anywhere">{query.data.error}</Text>}
      </VStack>
        </ModalBody>
        <ModalFooter gap={2} flexWrap="wrap">
          <RelayHelp label={t("nodes.relay.applyLabel")} help={t("nodes.relay.applyHelp")} />
          <Button type="button" size="sm" onClick={closeManager} isDisabled={save.isLoading}>{t("cancel")}</Button>
          <Button type="button" size="sm" colorScheme="primary" isLoading={save.isLoading} isDisabled={!canSave || !dirty} onClick={() => save.mutate()}>{t("nodes.relay.save")}</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  </>;
};
