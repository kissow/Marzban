import {
  Alert, AlertIcon, Button, FormControl, FormLabel, HStack, Input, Tooltip,
  Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader,
  ModalOverlay, Select, SimpleGrid, Stack, Text, useDisclosure, useToast,
} from "@chakra-ui/react";
import { AdjustmentsHorizontalIcon } from "@heroicons/react/24/outline";
import { FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { generateErrorMessage } from "utils/toastHandler";

type Protocol = "http" | "socks";
type UdpMode = "legacy" | "proxy" | "tcp_only";
type Egress = {
  configured: boolean;
  protocol?: Protocol;
  udp_mode?: UdpMode;
  server?: string;
  port?: number;
  username?: string;
  has_password?: boolean;
};
type FormState = {
  protocol: Protocol;
  udp_mode: UdpMode;
  server: string;
  port: string;
  username: string;
  password: string;
};

const formFrom = (egress?: Egress): FormState => ({
  protocol: egress?.protocol || "http",
  udp_mode: egress?.udp_mode || "legacy",
  server: egress?.server || "",
  port: String(egress?.port || 1080),
  username: egress?.username || "",
  password: "",
});

export const NodeEgressCard: FC<{ nodeId: number; nodeName: string; enabled?: boolean }> = ({
  nodeId, nodeName, enabled = true,
}) => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const modal = useDisclosure();
  const [form, setForm] = useState<FormState>(formFrom());
  const queryKey = ["node-egress", nodeId];
  const { data } = useQuery<Egress>(queryKey, () => fetch(`/node/${nodeId}/egress`), {
    enabled, retry: false,
  });

  const save = useMutation(() => fetch(`/node/${nodeId}/egress`, {
    method: "PUT",
    body: {
      protocol: form.protocol,
      udp_mode: form.udp_mode,
      server: form.server.trim(),
      port: Number(form.port),
      username: form.username.trim() || null,
      password: form.password || null,
    },
  }), {
    onSuccess: () => {
      queryClient.invalidateQueries(queryKey);
      modal.onClose();
      toast({ status: "success", title: t("nodes.egress.saved") });
    },
    onError: (error) => { generateErrorMessage(error, toast); },
  });

  const clear = useMutation(() => fetch(`/node/${nodeId}/egress`, { method: "DELETE" }), {
    onSuccess: () => {
      queryClient.invalidateQueries(queryKey);
      modal.onClose();
      toast({ status: "success", title: t("nodes.egress.cleared") });
    },
    onError: (error) => { generateErrorMessage(error, toast); },
  });

  const openManager = () => {
    setForm(formFrom(data));
    modal.onOpen();
  };
  const set = (key: keyof FormState, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));
  const port = Number(form.port);
  const credentialsValid = (!form.username.trim() && !form.password) || Boolean(
    form.username.trim() && (form.password ||
      (data?.has_password && form.username.trim() === (data.username || "")))
  );
  const canSave = Boolean(form.server.trim() && Number.isInteger(port) && port >= 1 && port <= 65535 && credentialsValid);

  return <>
    <HStack w="full" minH="38px" justify="space-between" borderWidth="1px"
      borderColor="gray.200" _dark={{ borderColor: "gray.600" }} borderRadius="md" px={3} py={2}>
      <HStack spacing={2} minW={0}>
        <AdjustmentsHorizontalIcon width="18" />
        <Text fontSize="sm" fontWeight="medium" noOfLines={1}>{t("nodes.egress.title")}</Text>
        {data && <Text fontSize="xs" color="gray.500" flexShrink={0} display={{ base: "none", sm: "block" }}>
          {data?.configured ? t("nodes.egress.configured") : t("nodes.egress.empty")}
        </Text>}
      </HStack>
      <Button type="button" size="xs" variant="outline" colorScheme="primary" onClick={openManager}
        isDisabled={!enabled || !data} flexShrink={0}>{t("nodes.egress.manage")}</Button>
    </HStack>

    <Modal isOpen={modal.isOpen} onClose={modal.onClose} size="lg" isCentered scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent mx={3}>
        <ModalHeader fontSize="md">{nodeName} · {t("nodes.egress.manage")}</ModalHeader>
        <ModalCloseButton />
        <ModalBody pt={0}>
          <Alert status="info" mb={4} borderRadius="md" alignItems="flex-start">
            <AlertIcon /><Text fontSize="xs">{t("nodes.egress.hint")}</Text>
          </Alert>
          <Stack spacing={3}>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
              <FormControl>
                <FormLabel fontSize="sm">{t("nodes.egress.protocol")}</FormLabel>
                <Select size="sm" value={form.protocol}
                  onChange={(e) => setForm((current) => ({ ...current,
                    protocol: e.target.value as Protocol,
                    udp_mode: e.target.value === "http" && current.udp_mode === "proxy" ? "legacy" : current.udp_mode,
                  }))}>
                  <option value="http">HTTP</option><option value="socks">SOCKS5</option>
                </Select>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>
                  {t("nodes.egress.udpMode")}
                  <Tooltip label={t("nodes.egress.udpHelp")} hasArrow placement="top">
                    <Text as="span" tabIndex={0} aria-label={t("nodes.egress.udpHelp")}
                      fontSize="xs" color="gray.500" cursor="help">ⓘ</Text>
                  </Tooltip>
                </FormLabel>
                <Select size="sm" value={form.udp_mode} onChange={(e) => set("udp_mode", e.target.value)}>
                  <option value="legacy">{t("nodes.egress.udpLegacy")}</option>
                  <option value="proxy" disabled={form.protocol !== "socks"}>{t("nodes.egress.udpProxy")}</option>
                  <option value="tcp_only">{t("nodes.egress.udpTcpOnly")}</option>
                </Select>
              </FormControl>
              <FormControl isRequired>
                <FormLabel fontSize="sm">{t("nodes.egress.server")}</FormLabel>
                <Input size="sm" value={form.server} placeholder="proxy.example.com"
                  onChange={(e) => set("server", e.target.value)} />
              </FormControl>
              <FormControl isRequired>
                <FormLabel fontSize="sm">{t("nodes.egress.port")}</FormLabel>
                <Input size="sm" type="number" value={form.port}
                  onChange={(e) => set("port", e.target.value)} />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">{t("nodes.egress.username")}</FormLabel>
                <Input size="sm" value={form.username}
                  onChange={(e) => set("username", e.target.value)} />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm" display="flex" alignItems="center" gap={2}>
                  {t("nodes.egress.passwordShort")}
                  <Tooltip label={t("nodes.egress.password")} hasArrow placement="top">
                    <Text as="span" tabIndex={0} aria-label={t("nodes.egress.password")}
                      fontSize="xs" color="gray.500" cursor="help">ⓘ</Text>
                  </Tooltip>
                </FormLabel>
                <Input size="sm" type="password" value={form.password}
                  placeholder={data?.has_password ? "••••••••" : ""}
                  onChange={(e) => set("password", e.target.value)} />
              </FormControl>
            </SimpleGrid>
          </Stack>
        </ModalBody>
        <ModalFooter gap={2} flexWrap="wrap">
          {data?.configured && <Button size="sm" variant="ghost" colorScheme="red" mr="auto"
            onClick={() => clear.mutate()} isLoading={clear.isLoading}>
            {t("nodes.egress.clear")}
          </Button>}
          <Button size="sm" onClick={modal.onClose}>{t("cancel")}</Button>
          <Button size="sm" colorScheme="primary" onClick={() => save.mutate()}
            isLoading={save.isLoading} isDisabled={!canSave}>
            {t("nodes.egress.save")}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  </>;
};
