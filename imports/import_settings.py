# Настройки подключения к Oracle ДБ
from django.urls import conf


username = 'PPSREPORT'
password = 'A89AFC78'
dsn = 'ora.rskh.local/PPS'
port = 1512
encoding = 'UTF-8'
# Вариант конфигурации отображения 1 - Обычная шахматка; 2 - Шахматка на неделю
table_config = 1
#Количество строк на отображение
rows_on_page=9
