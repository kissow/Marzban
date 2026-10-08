import { useEffect, useState } from "react";
import {
  Alert, AlertIcon, Badge, Box, Button, FormLabel, HStack, Icon,
  IconButton, SimpleGrid, Text, Tooltip, useToast,
} from "@chakra-ui/react";
import { InformationCircleIcon } from "@heroicons/react/24/outline";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { generateErrorMessage } from "utils/toastHandler";
import { parseMainUsageRate, syncMainUsageDraft } from "utils/mainUsage";
import { Input } from "./Input";

type Settings = { usage_coefficient: number };
const queryKey = "main-usage-settings";

// A separate local-core setting; never submits or changes a remote Node form.
export function MainUsageCard({ enabled }: { enabled: boolean }) {
  const { t } = useTranslation();
  const toast = useToast();
  const client = useQueryClient();
  const query = useQuery<Settings>(queryKey, () => fetch("/node/main/usage"), {
    enabled, retry: false,
  });
  const [rate, setRate] = useState(() => query.data ? String(query.data.usage_coefficient) : "");
  const [dirty, setDirty] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [helpPinned, setHelpPinned] = useState(false);
  useEffect(() => {
    if (query.data) setRate(current => syncMainUsageDraft(current, dirty, query.data!.usage_coefficient));
  }, [query.data, dirty]);
  const numericRate = parseMainUsageRate(rate);
  const save = useMutation(() => fetch<Settings>("/node/main/usage", {
    method: "PUT", body: { usage_coefficient: numericRate },
  }), {
    onSuccess: result => {
      client.setQueryData(queryKey, result);
      setRate(String(result.usage_coefficient));
      setDirty(false);
      toast({ status: "success", title: t("nodes.mainUsage.saved") });
    },
    onError: error => { generateErrorMessage(error, toast); },
  });
  const canSave = dirty && numericRate !== null && numericRate !== query.data?.usage_coefficient
    && !!query.data && !query.isError && !query.isFetching && !save.isLoading;
  return <Box borderWidth="1px" borderColor="gray.200" _dark={{ borderColor: "gray.600" }}
    borderRadius="4px" p={3} mb={4} w="full" data-testid="main-usage-card">
    <HStack justify="space-between" spacing={2} mb={3}>
      <Text fontSize="sm" fontWeight="medium">{t("nodes.mainUsage.title")}</Text>
      <Badge colorScheme="blue" borderRadius="full" px={3} py={1} fontSize="0.7rem">{t("nodes.mainUsage.badge")}</Badge>
    </HStack>
    {query.isError && <Alert status="error" mb={3}><AlertIcon />
      <Text flex={1} fontSize="xs">{t("nodes.mainUsage.loadFailed")}</Text>
      <Button type="button" size="xs" onClick={() => query.refetch()}>{t("nodes.relay.retry")}</Button>
    </Alert>}
    <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={3} alignItems="end">
      <Box minW={0}>
        <FormLabel htmlFor="main-usage-rate" display="flex" alignItems="center" gap={1}>
          {t("nodes.mainUsage.coefficient")}
          <Tooltip label={t("nodes.mainUsage.help")} hasArrow placement="top" isOpen={helpOpen}
            maxW="min(320px, calc(100vw - 32px))" whiteSpace="normal" overflowWrap="anywhere">
            <IconButton type="button" aria-label={t("nodes.mainUsage.helpLabel")} aria-expanded={helpOpen}
              variant="unstyled" display="inline-flex" alignItems="center" justifyContent="center"
              minW="24px" h="24px" color="gray.400" icon={<Icon as={InformationCircleIcon} boxSize={4} />}
              onMouseEnter={() => setHelpOpen(true)} onMouseLeave={() => { if (!helpPinned) setHelpOpen(false); }}
              onFocus={() => setHelpOpen(true)} onBlur={() => { setHelpPinned(false); setHelpOpen(false); }}
              onClick={() => { setHelpPinned(!helpPinned); setHelpOpen(!helpPinned); }}
              onKeyDown={event => { if (event.key === "Escape" && helpOpen) {
                event.stopPropagation(); setHelpPinned(false); setHelpOpen(false);
              } }} />
          </Tooltip>
        </FormLabel>
        <Input id="main-usage-rate" name="main_usage_coefficient" type="number" size="sm" step={0.1}
          value={rate} disabled={!query.data || query.isError || save.isLoading}
          onChange={value => { setDirty(true); setRate(typeof value === "string" ? value : String(value?.target?.value ?? "")); }}
          error={dirty && numericRate === null ? t("nodes.mainUsage.invalid") : undefined} />
      </Box>
      <Button type="button" colorScheme="primary" size="sm" isDisabled={!canSave}
        isLoading={save.isLoading || query.isLoading} onClick={() => { if (canSave) save.mutate(); }}>
        {t("nodes.mainUsage.save")}
      </Button>
    </SimpleGrid>
    <Text mt={2} fontSize="xs" color="gray.500" _dark={{ color: "gray.400" }} aria-live="polite">
      {numericRate !== null ? t("nodes.mainUsage.example", { rate: numericRate }) : t("nodes.mainUsage.enterRate")}
    </Text>
  </Box>;
}
