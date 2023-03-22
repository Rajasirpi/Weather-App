from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap

from MainWindow import Ui_MainWindow

from datetime import datetime
import calendar
import json
import os
import sys
import requests
from urllib.parse import urlencode

OPENWEATHERMAP_API_KEY = '9a7e3f328dd39476b74bfa95cfaaf302'

"""
Get an API key from https://openweathermap.org/ to use with this
application.

"""


def from_ts_to_time_of_day(ts):
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M").lstrip("0")


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.
    '''
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(dict, dict)

class WeatherWorker(QRunnable):
    '''
    Worker thread for weather updates.
    '''
    signals = WorkerSignals()
    is_interrupted = False

    def __init__(self, location):
        super(WeatherWorker, self).__init__()
        self.location = location

    @pyqtSlot()
    def run(self):
        try:
            params = dict(
                q=self.location,
                appid=OPENWEATHERMAP_API_KEY
            )

            url = 'http://api.openweathermap.org/data/2.5/weather?%s&units=metric' % urlencode(params)
            r = requests.get(url)
            weather = json.loads(r.text)

            # Check if we had a failure (the forecast will fail in the same way).
            if weather['cod'] != 200:
                raise Exception(weather['message'])

            url = 'http://api.openweathermap.org/data/2.5/forecast?%s&units=metric' % urlencode(params)
            r = requests.get(url)
            forecast = json.loads(r.text)

            self.signals.result.emit(weather, forecast)

        except Exception as e:
            self.signals.error.emit(str(e))

        self.signals.finished.emit()



class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.pushButton.pressed.connect(self.update_weather)

        self.threadpool = QThreadPool()

        self.show()


    def alert(self, message):
        alert = QMessageBox.warning(self, "Warning", message)

    def update_weather(self):
        worker = WeatherWorker(self.lineEdit.text())
        worker.signals.result.connect(self.weather_result)
        worker.signals.error.connect(self.alert)
        self.threadpool.start(worker)

    def weather_result(self, weather, forecasts):
        self.windLabel.setText("%.2f m/s" % weather['wind']['speed'])

        self.temperatureLabel.setText("%.1f °C" % weather['main']['temp'])
        # self.pressureLabel.setText("%d" % weather['main']['pressure'])
        self.humidityLabel.setText("%d" % weather['main']['humidity'])
        pb = weather['main']['humidity']
        self.progressBar.setProperty("value", pb)
        self.sunriseLabel.setText(from_ts_to_time_of_day(weather['sys']['sunrise']))
        self.sunsetLabel.setText(from_ts_to_time_of_day(weather['sys']['sunset']))
        self.weatherLabel.setText("%s (%s)" % (
            weather['weather'][0]['main'],
            weather['weather'][0]['description']
        )
                                  )

        self.set_weather_icon(self.weatherIcon, weather['weather'])
        time = weather['dt']
        dt = datetime.fromtimestamp(time)
        ds_time = calendar.month_name[dt.month]+' '+ str(dt.day)+' '+str(dt.year)+' '+dt.strftime("%H:%M")
        self.timeLabel.setText(ds_time)

        for n, forecast in enumerate(forecasts['list'][:7], 1):
            getattr(self, 'forecastTime%d' % n).setText(from_ts_to_time_of_day(forecast['dt']))
            self.set_weather_icon(getattr(self, 'forecastIcon%d' % n), forecast['weather'])
            getattr(self, 'forecastTemp%d' % n).setText("%.1f °C" % forecast['main']['temp'])

    def set_weather_icon(self, label, weather):
        label.setPixmap(
            QPixmap(os.path.join('images', "%s.png" %
                                 weather[0]['icon']
                                 )
                    )
        )
        self.sunsetIcon.setPixmap(QPixmap(os.path.join('images', "sunset.png")))
        self.sunriseIcon.setPixmap(QPixmap(os.path.join('images', "sunrise.png")))
        self.bcimage.setPixmap(QPixmap(os.path.join('images', "bluesky.jpg")))
        self.windspeed.setPixmap(QPixmap(os.path.join('images', "ws.png")))
        self.windirection.setPixmap(QPixmap(os.path.join('images', "wd.png")))

if __name__ == '__main__':

    app = QApplication([])
    window = MainWindow()
    app.exec_()