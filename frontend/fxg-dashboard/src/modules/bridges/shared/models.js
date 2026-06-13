/**
 * Shared bridge status models - single source of truth.
 * Used by both canonical_mac_file_bridge_v1 and parallel_windows_sidecar_bridge_v1.
 */

export const BRIDGE_IDS = {
  CANONICAL: 'canonical_mac_file_bridge_v1',
  WINDOWS_SIDECAR: 'parallel_windows_sidecar_bridge_v1',
  MOCK_SIDECAR: 'mock_sidecar_ui_validation_only',
};

export const BRIDGE_FAMILIES = {
  canonical_mac_file_bridge: 'canonical_mac_file_bridge',
  windows_sidecar_bridge: 'windows_sidecar_bridge',
};

export const BRIDGE_ROLES = {
  execution_signal_bridge: 'execution_signal_bridge',
  account_price_diagnostics_bridge: 'account_price_diagnostics_bridge',
};

/** @typedef {Object} NormalizedBridgeStatus */
/** @typedef {{ bridge_id: string, bridge_family: string, bridge_role: string, machine: string, enabled: boolean, healthy: boolean, degraded: boolean, failure_bucket: string|null, recommended_fix: string|null }} NormalizedBridgeStatus */
