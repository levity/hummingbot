import json
import unittest
from datetime import datetime, time
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import yaml
from pydantic import ValidationError, validate_model

from hummingbot.client.config.config_data_types import BaseClientModel
from hummingbot.client.config.config_helpers import retrieve_validation_error_msg
from hummingbot.client.settings import AllConnectorSettings
from hummingbot.strategy.avellaneda_market_making.avellaneda_market_making_config_map_pydantic import (
    AvellanedaMarketMakingConfigMap,
    DailyBetweenTimesModel,
    FromDateToDateModel,
    InfiniteModel,
)


class AvellanedaMarketMakingConfigMapPydanticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.exchange = "binance"
        cls.base_asset = "COINALPHA"
        cls.quote_asset = "HBOT"
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"

    def setUp(self) -> None:
        super().setUp()
        config_settings = self.get_default_map()
        self.config_map = AvellanedaMarketMakingConfigMap(**config_settings)

    def get_default_map(self) -> Dict[str, str]:
        config_settings = {
            "exchange": self.exchange,
            "market": self.trading_pair,
            "execution_timeframe_model": {
                "start_time": "09:30:00",
                "end_time": "16:00:00",
            },
            "order_amount": "10",
            "order_optimization_enabled": "yes",
            "risk_factor": "0.5",
            "order_refresh_time": "60",
            "inventory_target_base_pct": "50",
        }
        return config_settings

    def test_schema_encoding_removes_client_data_functions(self):
        s = AvellanedaMarketMakingConfigMap.schema_json()
        j = json.loads(s)
        expected = {
            "prompt": None,
            "prompt_on_new": True,
        }
        self.assertEqual(expected, j["properties"]["market"]["client_data"])

    def test_initial_sequential_build(self):
        config_map: AvellanedaMarketMakingConfigMap = AvellanedaMarketMakingConfigMap.construct()
        config_settings = self.get_default_map()

        def build_config_map(cm: BaseClientModel, cs: Dict):
            """This routine can be used in the create command, with slight modifications."""
            for key, field in cm.__fields__.items():
                client_data = cm.get_client_data(key)
                if client_data is not None and client_data.prompt_on_new:
                    self.assertIsInstance(client_data.prompt(cm), str)
                    if key == "execution_timeframe_model":
                        cm.__setattr__(key, "daily_between_times")  # simulate user input
                    else:
                        cm.__setattr__(key, cs[key])
                    new_value = cm.__getattribute__(key)
                    if isinstance(new_value, BaseClientModel):
                        build_config_map(new_value, cs[key])

        build_config_map(config_map, config_settings)
        validate_model(config_map.__class__, config_map.__dict__)

    def test_order_amount_prompt(self):
        prompt = self.config_map.get_client_prompt("order_amount")
        expected = f"What is the amount of {self.base_asset} per order?"

        self.assertEqual(expected, prompt)

    def test_maker_trading_pair_prompt(self):
        exchange = self.config_map.exchange
        example = AllConnectorSettings.get_example_pairs().get(exchange)

        prompt = self.config_map.get_client_prompt("market")
        expected = f"Enter the token trading pair you would like to trade on {exchange} (e.g. {example})"

        self.assertEqual(expected, prompt)

    def test_execution_time_prompts(self):
        self.config_map.execution_timeframe_model = FromDateToDateModel.Config.title
        model = self.config_map.execution_timeframe_model
        prompt = model.get_client_prompt("start_datetime")
        expected = "Please enter the start date and time (YYYY-MM-DD HH:MM:SS)"
        self.assertEqual(expected, prompt)
        prompt = model.get_client_prompt("end_datetime")
        expected = "Please enter the end date and time (YYYY-MM-DD HH:MM:SS)"
        self.assertEqual(expected, prompt)

        self.config_map.execution_timeframe_model = DailyBetweenTimesModel.Config.title
        model = self.config_map.execution_timeframe_model
        prompt = model.get_client_prompt("start_time")
        expected = "Please enter the start time (HH:MM:SS)"
        self.assertEqual(expected, prompt)
        prompt = model.get_client_prompt("end_time")
        expected = "Please enter the end time (HH:MM:SS)"
        self.assertEqual(expected, prompt)

    @patch(
        "hummingbot.strategy.avellaneda_market_making"
        ".avellaneda_market_making_config_map_pydantic.validate_market_trading_pair"
    )
    def test_validators(self, validate_market_trading_pair_mock):

        with self.assertRaises(ValidationError) as e:
            self.config_map.exchange = "test-exchange"

        error_msg = "Invalid exchange, please choose value from "
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertTrue(actual_msg.startswith(error_msg))

        alt_pair = "ETH-USDT"
        error_msg = "Failed"
        validate_market_trading_pair_mock.side_effect = (
            lambda m, v: None if v in [self.trading_pair, alt_pair] else error_msg
        )

        self.config_map.market = alt_pair
        self.assertEqual(alt_pair, self.config_map.market)

        with self.assertRaises(ValidationError) as e:
            self.config_map.market = "XXX-USDT"

        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertTrue(actual_msg.startswith(error_msg))

        self.config_map.execution_timeframe_model = "infinite"
        self.assertIsInstance(self.config_map.execution_timeframe_model, InfiniteModel)

        self.config_map.execution_timeframe_model = "from_date_to_date"
        self.assertIsInstance(self.config_map.execution_timeframe_model, FromDateToDateModel)

        self.config_map.execution_timeframe_model = "daily_between_times"
        self.assertIsInstance(self.config_map.execution_timeframe_model, DailyBetweenTimesModel)

        with self.assertRaises(ValidationError) as e:
            self.config_map.execution_timeframe_model = "XXX"

        error_msg = (
            "Invalid timeframe, please choose value from ['infinite', 'from_date_to_date', 'daily_between_times']"
        )
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        self.config_map.execution_timeframe_model = "from_date_to_date"
        model = self.config_map.execution_timeframe_model
        model.start_datetime = "2021-01-01 12:00:00"
        model.end_datetime = "2021-01-01 15:00:00"

        self.assertEqual(datetime(2021, 1, 1, 12, 0, 0), model.start_datetime)
        self.assertEqual(datetime(2021, 1, 1, 15, 0, 0), model.end_datetime)

        with self.assertRaises(ValidationError) as e:
            model.start_datetime = "2021-01-01 30:00:00"

        error_msg = "Incorrect date time format (expected is YYYY-MM-DD HH:MM:SS)"
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        with self.assertRaises(ValidationError) as e:
            model.start_datetime = "12:00:00"

        error_msg = "Incorrect date time format (expected is YYYY-MM-DD HH:MM:SS)"
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        self.config_map.execution_timeframe_model = "daily_between_times"
        model = self.config_map.execution_timeframe_model
        model.start_time = "12:00:00"

        self.assertEqual(time(12, 0, 0), model.start_time)

        with self.assertRaises(ValidationError) as e:
            model.start_time = "30:00:00"

        error_msg = "Incorrect time format (expected is HH:MM:SS)"
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        with self.assertRaises(ValidationError) as e:
            model.start_time = "2021-01-01 12:00:00"

        error_msg = "Incorrect time format (expected is HH:MM:SS)"
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        self.config_map.order_levels_mode = "multi_order_level"
        model = self.config_map.order_levels_mode

        with self.assertRaises(ValidationError) as e:
            model.order_levels = 1

        error_msg = "Value cannot be less than 2."
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        model.order_levels = 3
        self.assertEqual(3, model.order_levels)

        self.config_map.hanging_orders_mode = "track_hanging_orders"
        model = self.config_map.hanging_orders_mode

        with self.assertRaises(ValidationError) as e:
            model.hanging_orders_cancel_pct = "-1"

        error_msg = "Value must be between 0 and 100 (exclusive)."
        actual_msg = retrieve_validation_error_msg(e.exception)
        self.assertEqual(error_msg, actual_msg)

        model.hanging_orders_cancel_pct = "3"
        self.assertEqual(3, model.hanging_orders_cancel_pct)

    def test_load_configs_from_yaml(self):
        cur_dir = Path(__file__).parent
        f_path = cur_dir / "test_config.yml"

        with open(f_path, "r") as file:
            data = yaml.safe_load(file)

        loaded_config_map = AvellanedaMarketMakingConfigMap(**data)

        self.assertEqual(self.config_map, loaded_config_map)