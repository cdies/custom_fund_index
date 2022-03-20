const log = console.log;

let interval = document.querySelector('input[name="interval"]:checked').value;
let currInterval = interval

const chartProperties = {
  width: 1450,
  height: 600,
  timeScale: {
    timeVisible: true,
    secondsVisible: false,
  }
};

const domElement = document.getElementById('custom_chart');
const chart = LightweightCharts.createChart(domElement, chartProperties);
const candleSeries = chart.addCandlestickSeries()


// History
function getHistory(interval) {
  fetch(`http://127.0.0.1:8000/api/historical_candles/` + interval)
    .then(res => res.json())
    .then(json_str => JSON.parse(json_str))
    .then(data => {
      // log(data);

      for (let i = 0; i < data.length; ++i) {
        data[i].time = data[i].time / 1000 + 10800; // localize to Moscow time 60*60*3 = 10800 
      };

      candleSeries.setData(data);
    })
    .catch(err => log(err))
}

getHistory(interval);


// Dynamic Chart
setInterval(function () {
  currInterval = document.querySelector('input[name="interval"]:checked').value;

  if (currInterval != interval) {
    getHistory(currInterval);
    interval = currInterval;
  }

  fetch(`http://127.0.0.1:8000/api/currient_candle/` + interval)
    .then(res => res.json())
    .then(json_str => JSON.parse(json_str))
    .then(data => {

      log(data);

      data.time = data.time / 1000 + 10800 // localize to Moscow time 60*60*3 = 10800

      candleSeries.update(data);
    })
    .catch(err => log(err))
}, 1000); // <-- Увеличивай интервал здесь!
/*

Если задержку не поставить, будет очень много ошибок.
Подробнее про ограничения см здесь: https://tinkoff.github.io/investAPI/limits/
1000 - это 1 секунда

С этим параметром можно играть, увеличивая или уменьшая его.

*/