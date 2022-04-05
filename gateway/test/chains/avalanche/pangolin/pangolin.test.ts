jest.useFakeTimers();
import { Pangolin } from '../../../../src/connectors/pangolin/pangolin';
import { patch, unpatch } from '../../../services/patch';
import { UniswapishPriceError } from '../../../../src/services/error-handler';
import {
  Fetcher,
  Pair,
  Route,
  Token,
  TokenAmount,
  Trade,
  TradeType,
} from '@pangolindex/sdk';
import { BigNumber } from 'ethers';
import { Avalanche } from '../../../../src/chains/avalanche/avalanche';

let avalanche: Avalanche;
let pangolin: Pangolin;

const WETH = new Token(
  43114,
  '0xd0A1E359811322d97991E03f863a0C30C2cF029C',
  18,
  'WETH'
);

const WAVAX = new Token(
  43114,
  '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7',
  18,
  'WAVAX'
);

beforeAll(async () => {
  avalanche = Avalanche.getInstance('fuji');
  await avalanche.init();
  pangolin = Pangolin.getInstance('avalanche', 'fuji');
  patch(pangolin, '_poolStrings', []); // this avoids pangolin from trying to download pool data
  await pangolin.init();
});

afterEach(() => {
  unpatch();
});

const patchFetchPairData = () => {
  patch(Fetcher, 'fetchPairData', () => {
    return new Pair(
      new TokenAmount(WETH, '2000000000000000000'),
      new TokenAmount(WAVAX, '1000000000000000000'),
      43114
    );
  });
};

const patchTrade = (key: string, error?: Error) => {
  patch(Trade, key, () => {
    if (error) return [];
    const WETH_WAVAX = new Pair(
      new TokenAmount(WETH, '2000000000000000000'),
      new TokenAmount(WAVAX, '1000000000000000000'),
      43114
    );
    const WAVAX_TO_WETH = new Route([WETH_WAVAX], WAVAX);
    return [
      new Trade(
        WAVAX_TO_WETH,
        new TokenAmount(WAVAX, '1000000000000000'),
        TradeType.EXACT_INPUT,
        43114
      ),
    ];
  });
};

describe('verify Pangolin estimateSellTrade', () => {
  it('Should return an ExpectedTrade when available', async () => {
    patchFetchPairData();
    patchTrade('bestTradeExactIn');

    const expectedTrade = await pangolin.estimateSellTrade(
      WETH,
      WAVAX,
      BigNumber.from(1)
    );
    expect(expectedTrade).toHaveProperty('trade');
    expect(expectedTrade).toHaveProperty('expectedAmount');
  });

  it('Should throw an error if no pair is available', async () => {
    patchFetchPairData();
    patchTrade('bestTradeExactIn', new Error('error getting trade'));

    await expect(async () => {
      await pangolin.estimateSellTrade(WETH, WAVAX, BigNumber.from(1));
    }).rejects.toThrow(UniswapishPriceError);
  });
});

describe('verify Pangolin estimateBuyTrade', () => {
  it('Should return an ExpectedTrade when available', async () => {
    patchFetchPairData();
    patchTrade('bestTradeExactOut');

    const expectedTrade = await pangolin.estimateBuyTrade(
      WETH,
      WAVAX,
      BigNumber.from(1)
    );
    expect(expectedTrade).toHaveProperty('trade');
    expect(expectedTrade).toHaveProperty('expectedAmount');
  });

  it('Should return an error if no pair is available', async () => {
    patchFetchPairData();
    patchTrade('bestTradeExactOut', new Error('error getting trade'));

    await expect(async () => {
      await pangolin.estimateBuyTrade(WETH, WAVAX, BigNumber.from(1));
    }).rejects.toThrow(UniswapishPriceError);
  });
});
