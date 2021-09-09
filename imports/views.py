from django.http.response import HttpResponse
from django.shortcuts import render
import pyodbc
import cx_Oracle
from .import_settings import *
import datetime
from ctypes import *
# Create your views here.


def index(request):
    connection = None
    try:
        connection = cx_Oracle.connect(
            username,
            password,
            dsn,
            encoding=encoding
        )
        cur = connection.cursor()
        date_today = datetime.datetime.today()
        sql_date = date_today.strftime("%d.%m.%Y")
        cur.execute("SELECT TO_CHAR(lesson_time_in,'HH24'), coach_name, lesson_skill_type, lesson_type, TO_CHAR(lesson_time_in,'HH24:MI'), TO_CHAR(lesson_time_out,'HH24:MI'), lesson_count_clients, lesson_location_id FROM view_rosa_coach WHERE (lesson_status=3 OR lesson_status=1 AND lesson_group_id IS NOT NULL) AND lesson_date = TO_DATE('" +
                    str(sql_date)+"','DD.MM.YYYY HH24:MI:SS') AND TO_CHAR(lesson_time_in,'HH24') BETWEEN TO_CHAR(trunc(SYSDATE+1)+9/24,'HH24') AND TO_CHAR(trunc(SYSDATE)+86399/86400,'HH24') AND lesson_appl_id IN (5) ORDER BY TO_CHAR(lesson_time_in,'HH24'), coach_name, TO_CHAR(lesson_time_in,'HH24:MI')")
        res = cur.fetchall()
        instructors_shedule_data_in = ''
        # Готовим SQL-запрос для импорта в MSSQL
        # Подключаемся к MSSQL
        try:
            cnxn = pyodbc.connect(
                'DRIVER=ODBC Driver 17 for SQL Server;SERVER=agRosaPlan.rskh.local;DATABASE=RosaPlan;Trusted_Connection=yes')
        except pyodbc.Error as ex:
            sqlstate=ex.args[1]
            output='<h1>Ой! Ошибочка вышла! '+str(sqlstate)+' Перезагрузка!!1</h1><script>$(document).ready(function(){await sleep(10000);window.location.reload(true);})</script>'
        cursor = cnxn.cursor()
        # Проверяем есть ли таблица в которую мы будем импортировать данные, если ее нет, то создаем ее
        cursor.execute(
            "if NOT EXISTS (SELECT * FROM sysobjects WHERE id=OBJECT_ID(N'[dbo].[instructors_shedule]') AND OBJECTPROPERTY(id, N'isUserTable')=1) CREATE TABLE [dbo].[instructors_shedule](lesson_hour int NOT NULL, coach_name varchar(255), lesson_skill_type varchar(255), lesson_type varchar(255), lesson_time_in varchar(255), lesson_time_out varchar(255), lesson_count_clients int, lesson_placement varchar(255))")
        cnxn.commit()
        # Очищаем таблицу от старых данных
        cursor.execute(
            "IF EXISTS (SELECT * FROM sysobjects WHERE id=OBJECT_ID(N'[dbo].[instructors_shedule]') AND OBJECTPROPERTY(id, N'isUserTable')=1) TRUNCATE TABLE [dbo].[instructors_shedule]")
        cnxn.commit()
        # Готовим строку для импорта
        import_string = "INSERT INTO instructors_shedule (lesson_hour, coach_name, lesson_skill_type, lesson_type, lesson_time_in, lesson_time_out, lesson_count_clients, lesson_placement) Values"
        for row in res:
            instructors_shedule_data_in += "("+str(row[0])+", '"+str(row[1])+"', '"+str(row[2])+"', '"+str(
                row[3])+"', '"+str(row[4])+"', '"+str(row[5])+"', "+str(row[6])+", '"+str(row[7])+"'),"
        # Обрезаем последнюю запятую
        l = len(instructors_shedule_data_in)
        instructors_shedule_data_in = instructors_shedule_data_in[:l-1]
        # Объединям строки для формирования SQL-запроса
        import_string += instructors_shedule_data_in
        # Вставляем в MSSQL данные
        cursor.execute(import_string)
        cnxn.commit()
        # Получаем по какому варианту конфигурации будем отображать таблицу
        if table_config == 1:
            # Выводим шахматку на день
            width = windll.user32.GetSystemMetrics(0)
            hight = windll.user32.GetSystemMetrics(1)
            output = '<h1>Таблица расписания инструкторов</h1>'
            output += '<table width="100%" cellpadding="0" cellspacing="0" border="0">'
            # Выводим заголовок таблицы
            output += '<tr><th rowspan="2" class="fio_th">ФИО Инструктора</th>'
            # Считаем количество ячеек для временной шкалы
            time_now = datetime.datetime.now()
            # hour = time_now.strftime('%H')
            hour = 9
            hours = 24-int(hour)
            cells = hours*4
            # for i in range(0, hours):
            output += '<th colspan="'+str(cells)+'">Часы занятий</th></tr>'
            output += '<tr>'
            for i in range(0, hours):
                output += '<th colspan="4" class="hour_th">'+str(hour)+'</th>'
                hour = int(hour)+1
            output += '</tr>'
            hour = 9
            # Готовим список инструкторов
            cursor.execute(
                "SELECT distinct coach_name FROM instructors_shedule")
            instructors_name = cursor.fetchall()
            row_counter = 0
            i = 0
            for instructor_name in instructors_name:
                output += '<tr class="hide'+str(row_counter)+'"><td class="fio_th">' + \
                    str(instructor_name.coach_name)+'</td>'
                # Для построения строки с занятиями получаем все занятия инструктора и ищем первую временную точку, так же проверяем минуты занятий.
                cursor.execute(
                    "SELECT TOP 1 lesson_skill_type, lesson_type, lesson_time_in, lesson_time_out, lesson_count_clients, lesson_placement FROM instructors_shedule where coach_name='"+str(instructor_name.coach_name)+"'")
                instructor_timeline = cursor.fetchall()
                cell_counter = 0
                for lesson in instructor_timeline:
                    lesson_start = lesson.lesson_time_in.split(':')
                    lesson_end = lesson.lesson_time_out.split(':')
                    # Отсчитываем начало во временной шкале
                    # Проверяем минуты на количество ячеек для добавления к часу. шаг 15 минут
                    if lesson_start[1] == '00':
                        cell_counter_add = 0
                    elif int(lesson_start[1]) > 0 and int(lesson_start[1]) <= 15:
                        cell_counter_add = 1
                    elif int(lesson_start[1]) > 15 and int(lesson_start[1]) <= 30:
                        cell_counter_add = 2
                    elif int(lesson_start[1]) > 30 and int(lesson_start[1]) <= 45:
                        cell_counter_add = 3
                    elif int(lesson_start[1]) > 45 and int(lesson_start[1]) <= 59:
                        cell_counter_add = 4
                    start_cell = (int(lesson_start[0])-hour)*4+cell_counter_add
                    cell_counter = start_cell
                    if int(lesson_start[0]) == 9 and str(lesson_start[1]) == '00':
                        output += ''
                    else:
                        output += '<td colspan="'+str(start_cell)+'"></td>'
                    # Отсчитываем количество ячеек для первого занятия
                    end_cell = (int(lesson_end[0])-int(lesson_start[0]))*4
                    cell_counter = cell_counter+end_cell
                    output += '<td colspan="'+str(end_cell)+'" class="lesson'
                    if str(lesson.lesson_type) == 'ГРП':
                        output += ' group'
                    output += '">'
                    # Тип инвентаря:
                    if str(lesson.lesson_skill_type) == 'Лыжи':
                        output += '<img src="/static/img/ski.png"/>'
                    elif str(lesson.lesson_skill_type) == 'Сноуборд':
                        output += '<img src="/static/img/board.png"/>'
                    if str(lesson.lesson_placement) == '1':
                        output += '<img src="/static/img/hotel.png"/>'
                    elif str(lesson.lesson_placement) == '2':
                        output += '<img src="/static/img/1600.png"/>'
                    # output+=str(lesson.lesson_skill_type)
                    # output+='</br>'+str(lesson.lesson_type)+'</br>'
                    output += '</br>'+str(lesson.lesson_time_in)+'-'+str(
                        lesson.lesson_time_out)+' Кол-во: '+str(lesson.lesson_count_clients)+'</td>'
                # Добиваем остальные ячейки занятий
                cursor.execute("SELECT lesson_skill_type, lesson_type, lesson_time_in, lesson_time_out, lesson_count_clients, lesson_placement FROM instructors_shedule where coach_name='" +
                               str(instructor_name.coach_name)+"' order by lesson_time_in OFFSET 1 ROW")
                other_lessons = cursor.fetchall()
                for other_lesson in other_lessons:
                    # Считаем разницу между занятиями
                    other_lesson_start = other_lesson.lesson_time_in.split(':')
                    other_lesson_end = other_lesson.lesson_time_out.split(':')
                    if other_lesson_start[1] == '00':
                        cell_counter_add = 0
                    elif int(other_lesson_start[1]) > 0 and int(other_lesson_start[1]) <= 15:
                        cell_counter_add = 1
                    elif int(other_lesson_start[1]) > 15 and int(other_lesson_start[1]) <= 30:
                        cell_counter_add = 2
                    elif int(other_lesson_start[1]) > 30 and int(other_lesson_start[1]) <= 45:
                        cell_counter_add = 3
                    elif int(other_lesson_start[1]) > 45 and int(other_lesson_start[1]) <= 59:
                        cell_counter_add = 4
                    other_lesson_start_cell = (
                        (int(other_lesson_start[0])-hour)*4+cell_counter_add)-cell_counter
                    other_lesson_end_cell = (
                        int(other_lesson_end[0])-int(other_lesson_start[0]))*4
                    cell_counter = cell_counter+other_lesson_start_cell+other_lesson_end_cell
                    if other_lesson_start_cell != 0:
                        output += '<td colspan="' + \
                            str(other_lesson_start_cell)+'"></td>'
                    output += '<td colspan="' + \
                        str(other_lesson_end_cell)+'" class="lesson'
                    if str(other_lesson.lesson_type) == 'ГРП':
                        output += ' group'
                    output += '">'
                    #'Тип инвентаря: '
                    # output+=str(lesson.lesson_skill_type)+'</br>'+str(other_lesson.lesson_type)
                    if str(other_lesson.lesson_skill_type) == 'Лыжи':
                        output += '<img src="/static/img/ski.png"/>'
                    elif str(other_lesson.lesson_skill_type) == 'Сноуборд':
                        output += '<img src="/static/img/board.png"/>'
                    if str(other_lesson.lesson_placement) == '1':
                        output += '<img src="/static/img/hotel.png"/>'
                    elif str(other_lesson.lesson_placement) == '2':
                        output += '<img src="/static/img/1600.png"/>'
                    output += '</br>'+str(other_lesson.lesson_time_in)+'-'+str(
                        other_lesson.lesson_time_out)+' Кол-во: '+str(other_lesson.lesson_count_clients)+'</td>'
                # Добиваем оставшиеся ячейки
                last_cells = 60-cell_counter
                output += '<td colspan="'+str(last_cells)+'"></td>'
                output += '</tr>'
                i = i+1
                if i == rows_on_page:
                    row_counter = row_counter+1
                    i = 0

            output += '</table>'
            # Готовим скрипт на отображение/скрытие строк
            output_script = '<script>'
            output_script += 'function sleep(ms){'
            output_script += 'return new Promise('
            output_script += 'resolve => setTimeout(resolve, ms)'
            output_script += ');'
            output_script += '}'
            output_script += 'async function carusel(){'
            if row_counter == 0:
                output_script += 'await sleep(10000);'
            else:
                output_script += 'await sleep(10000);'
                for circle in range(row_counter):
                    output_script += 'await sleep(10000);'
                    output_script += '$(".hide'+str(circle)+'").fadeOut(1000);'
                    output_script += 'await sleep(500);'
                    next_circle = circle+1
                    output_script += '$(".hide' + \
                        str(next_circle)+'").fadeIn(1000);'
                output_script += 'await sleep(10000);'
            output_script += 'window.location.reload(true);'
            output_script += '            }'
            output_script += '$(document).ready(function(){'
            output_script += 'carusel()'
            output_script += '})'
            output_script += '</script>'
            output += output_script
            # tratata
        # elif table_config == 2:
            # tratata

        cnxn.close()
        cur.close()
    except cx_Oracle.Error as error:
        print(error)
        return HttpResponse(error)
    finally:
        if connection:
            connection.close()
    data = {"content": output}

    return render(request, "home.html", context=data)
    # return render(request, "home.html")
