import { ConfigManagerV2 } from '../../services/config-manager-v2';
import { AvailableNetworks } from '../../services/config-manager-types';

export namespace PangolinConfig {
  export interface NetworkConfig {
    allowedSlippage: string;
    gasLimit: number;
    ttl: number;
    routerAddress: (network: string) => string;
    factoryAddress: (network: string) => string;
    tradingTypes: Array<string>;
    availableNetworks: Array<AvailableNetworks>;
    maxHops: (network: string) => number;
    pools: (network: string) => Array<string>;
  }

  export const config: NetworkConfig = {
    allowedSlippage: ConfigManagerV2.getInstance().get(
      'pangolin.allowedSlippage'
    ),
    gasLimit: ConfigManagerV2.getInstance().get('pangolin.gasLimit'),
    ttl: ConfigManagerV2.getInstance().get('pangolin.ttl'),
    routerAddress: (network: string) =>
      ConfigManagerV2.getInstance().get(
        'pangolin.contractAddresses.' + network + '.routerAddress'
      ),
    factoryAddress: (network: string) =>
      ConfigManagerV2.getInstance().get(
        'pangolin.contractAddresses.' + network + '.factoryAddress'
      ),
    tradingTypes: ['EVM_AMM'],
    availableNetworks: [
      { chain: 'avalanche', networks: ['avalanche', 'fuji'] },
    ],
    maxHops: (network: string) =>
      ConfigManagerV2.getInstance().get(`uniswap.pools.${network}.maxHops`),
    pools: (network: string) =>
      ConfigManagerV2.getInstance().get(`uniswap.pools.${network}.pools`),
  };
}
