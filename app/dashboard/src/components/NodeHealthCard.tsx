import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  HStack,
  Progress,
  SimpleGrid,
  Text,
  VStack,
} from "@chakra-ui/react";
import { FC } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";

type NodeHealthResponse = {
  node_id: number;
  status: "online" | "unknown";
  reason?: string | null;
  metrics?: {
    sampled_at: string;
    cpu_percent: number | null;
    memory_total_bytes: number | null;
    memory_used_bytes: number | null;
    disk_total_bytes: number | null;
    disk_used_bytes: number | null;
    uptime_seconds: number | null;
    active_users: number | null;
    memory_scope: string;
    disk_scope: string;
  } | null;
};

const formatBytes = (bytes: number | null) =>
  bytes === null ? "—" : `${(bytes / 1024 ** 3).toFixed(1)} GiB`;

const Metric: FC<{ label: string; value: string; percent?: number | null }> = ({
  label,
  value,
  percent,
}) => (
  <Box borderWidth="1px" borderColor="light-border" _dark={{ borderColor: "gray.600" }} borderRadius="md" p={2} minW={0}>
    <Text fontSize="xs" color="gray.500" noOfLines={1}>
      {label}
    </Text>
    <Text fontSize="sm" fontWeight="medium" mt={1} noOfLines={1}>
      {value}
    </Text>
    {percent !== undefined && percent !== null && <Progress value={percent} size="xs" mt={2} />}
  </Box>
);

export const NodeHealthCard: FC<{ nodeId: number; enabled: boolean }> = ({ nodeId, enabled }) => {
  const { t } = useTranslation();
  const { data, isLoading, isFetching, refetch } = useQuery<NodeHealthResponse>(
    ["node-health", nodeId],
    () => fetch(`/node/${nodeId}/health`),
    { enabled, refetchInterval: enabled ? 15000 : false, retry: false },
  );
  const metrics = data?.metrics;
  const memoryPercent =
    metrics?.memory_total_bytes && metrics.memory_used_bytes !== null
      ? (metrics.memory_used_bytes / metrics.memory_total_bytes) * 100
      : null;
  const diskPercent =
    metrics?.disk_total_bytes && metrics.disk_used_bytes !== null
      ? (metrics.disk_used_bytes / metrics.disk_total_bytes) * 100
      : null;

  return (
    <Alert status="info" alignItems="start" mb={4}>
      <AlertIcon />
      <AlertDescription w="full" overflow="hidden">
        <VStack align="stretch" spacing={2}>
          <HStack justify="space-between" flexWrap="wrap" gap={2}>
            <Text fontSize="sm" fontWeight="medium">
              {t("nodes.health.title")}
            </Text>
            <Button size="xs" variant="outline" onClick={() => refetch()} isLoading={isFetching}>
              {t("nodes.health.refresh")}
            </Button>
          </HStack>
          {!enabled ? (
            <Text fontSize="sm" color="gray.500">
              {t("nodes.health.offline")}
            </Text>
          ) : metrics ? (
            <>
              <SimpleGrid columns={{ base: 2, md: 4, xl: 5 }} spacing={2}>
                <Metric
                  label={t("nodes.health.cpu")}
                  value={metrics.cpu_percent === null ? "—" : `${metrics.cpu_percent.toFixed(1)}%`}
                  percent={metrics.cpu_percent}
                />
                <Metric
                  label={t("nodes.health.memory")}
                  value={`${formatBytes(metrics.memory_used_bytes)} / ${formatBytes(metrics.memory_total_bytes)}`}
                  percent={memoryPercent}
                />
                <Metric
                  label={t("nodes.health.disk")}
                  value={`${formatBytes(metrics.disk_used_bytes)} / ${formatBytes(metrics.disk_total_bytes)}`}
                  percent={diskPercent}
                />
                <Metric
                  label={t("nodes.health.uptime")}
                  value={
                    metrics.uptime_seconds === null
                      ? "—"
                      : `${Math.floor(metrics.uptime_seconds / 86400)} ${t("nodes.health.days")}`
                  }
                />
                <Metric
                  label={t("nodes.health.activeUsers")}
                  value={
                    metrics.active_users === null
                      ? t("nodes.health.activeUsersUnavailable")
                      : String(metrics.active_users)
                  }
                />
              </SimpleGrid>
              <Text fontSize="xs" color="gray.500">
                {t("nodes.health.scope", {
                  memory: metrics.memory_scope,
                  disk: metrics.disk_scope,
                })}
              </Text>
            </>
          ) : (
            <Text fontSize="sm" color="gray.500">
              {isLoading ? t("nodes.health.loading") : t(`nodes.health.reason.${data?.reason || "unavailable"}`)}
            </Text>
          )}
        </VStack>
      </AlertDescription>
    </Alert>
  );
};
