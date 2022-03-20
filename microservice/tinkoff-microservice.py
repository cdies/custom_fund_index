import pandas as pd
import numpy as np
from collections import defaultdict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from custom_index import CustomIndex


# Топ 5 самых дорогих акций из S&P 500
tickets = ['NVR', 'AMZN', 'GOOG', 'GOOGL', 'BKNG']

# Количество исторических дней для отображения
historical_days = 4

# Расчёт индекса
def compute_index(prices):
    mean_price = np.mean(prices)

    return mean_price


api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ci = CustomIndex(tickets, historical_days=historical_days, token='token.txt')

# Исторические данные
@api.get('/api/historical_candles/{interval}')
def historical_candles(interval: int):
    global ci

    # Средняя цена
    d = defaultdict(pd.DataFrame)

    # Собираем данные, все open от всех тикетов в один 
    # датафрейм, high в другой и т.д.
    def concat_columns(d, one_ticket_candles):
        for col in ['open', 'high', 'low', 'close']:
            d[col] = pd.concat([d[col], one_ticket_candles[col]], axis=1)

        return d        

    try:
        # Исторические данные для каждого тикета
        # скачиваем и обрабатываем отдельно
        for _, row in ci.df.iterrows():
            one_ticket_candles = ci.get_tinkoff_candles(row['figi'], interval)
            d = concat_columns(d, one_ticket_candles)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

            
    for col in ['open', 'high', 'low', 'close']:
        d[col] = d[col].sort_index(ascending=True)
        d[col] = d[col].fillna(method='ffill')
        d[col] = d[col].dropna()
        
        d[col] = d[col].apply(compute_index, axis=1)

    candles = pd.DataFrame(d)

    candles.index.name = 'time'
    candles.reset_index(inplace=True)

    ci.reset_last_candle()

    return candles.to_json(orient="records")


# Текущая цена
@api.get('/api/currient_candle/{interval}')
def currient_candle(interval: int):
    global ci

    curr_time = ci.round_to_minutes(pd.Timestamp.now(tz='Europe/Moscow'), interval)

    try:
        last_prices = ci.get_tinkoff_last_prices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    last_price = compute_index(last_prices)


    # формирование свечей по последней цене
    if curr_time > ci.last_candle['time']:
        # Новая свеча
        ci.reset_last_candle(open_price=last_price, time=curr_time)
    else:
        ci.last_candle['close'] = last_price

        if ci.last_candle['high'] < last_price:
            ci.last_candle['high'] = last_price

        elif ci.last_candle['low'] > last_price:
            ci.last_candle['low'] = last_price
    
    
    return ci.last_candle.to_json()