import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
from decimal import Decimal

from tinkoff.invest import Client, CandleInterval

import warnings
warnings.filterwarnings("ignore", 'This pattern has match groups')


class CustomIndex:

    def __init__(self, tickets, historical_days=2, token='token.txt'):
        self.logger = self.__create_logger()
        
        self.historical_days = historical_days
        self.reset_last_candle()

        try:
            with open(token, 'r') as file:
                self.__token = file.read().rstrip()
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> Ошибка в файле token.txt: '+ str(e))


        try:
            with Client(self.__token) as client:
                shares = client.instruments.shares() 
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> tinkoff api - Ошибка загрузки данных обо всех акциях.')

        shares = pd.DataFrame(shares.instruments)
        self.df = shares[shares['ticker'].isin(tickets)]


    def reset_last_candle(self, open_price=0.0, time=pd.Timestamp(0, tz='Europe/Moscow')):
        self.last_candle = pd.Series({'open': open_price, 
                                      'high': open_price, 
                                      'low': open_price, 
                                      'close': open_price, 
                                      'time': time})


    def round_to_minutes(self, t, interval=5):
        delta = pd.Timedelta(minutes=t.minute % interval, 
                            seconds=t.second, 
                            microseconds=t.microsecond)
        t -= delta
               
        return t


    def __units_nano_convert(self, d):
        # https://github.com/Tinkoff/invest-python/issues/45
        nano = d['nano'] / Decimal("10e8")
        price = d['units'] + float(nano)
        
        return price


    def __create_logger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.ERROR)
        
        formatter = logging.Formatter('--> %(asctime)s - %(name)s - %(levelname)s - %(message)s')

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)    
        logger.addHandler(sh)
        
        # send logs in docker logs
        fh = logging.FileHandler('/proc/1/fd/1')
        fh.setFormatter(formatter)    
        logger.addHandler(fh)

        return logger


    def get_tinkoff_candles(self, figi, interval):
        if interval == 1:
            interval = CandleInterval.CANDLE_INTERVAL_1_MIN
        elif interval == 5:
            interval = CandleInterval.CANDLE_INTERVAL_5_MIN
        elif interval == 15:
            interval = CandleInterval.CANDLE_INTERVAL_15_MIN
        else:
            interval = -1

        curr_time = datetime.now()
        data = []       
        

        for day in range(self.historical_days):
            try:
                with Client(self.__token) as client:
                    data += client.market_data.get_candles(
                        figi=figi,
                        from_=curr_time - timedelta(days=day+1),
                        to=curr_time - timedelta(days=day),
                        interval=interval
                    ).candles
            except Exception as e:
                self.logger.exception(e)
                raise Exception('--> tinkoff api - history - Ошибка загрузки исторических данных.')


        candles = pd.DataFrame(data)

        for col in ['open', 'high', 'low', 'close']:
            candles[col] = candles[col].apply(self.__units_nano_convert)

        candles = candles[['time', 'open', 'high', 'low', 'close']]

        candles['time'] = candles['time'].dt.tz_convert('Europe/Moscow')
        candles.set_index('time', inplace=True)

        candles = candles.drop_duplicates()
    
        return candles


    def get_tinkoff_last_prices(self):
        try:
            with Client(self.__token) as client:
                last_prices = client.market_data.get_last_prices(figi=self.df['figi'].to_list())
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> tinkoff api - last price - Ошибка загрузки последней цены.')

        last_prices = pd.DataFrame(last_prices.last_prices)

        last_prices = last_prices['price'].apply(self.__units_nano_convert)

        return last_prices
