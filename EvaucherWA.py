from flask import Flask, flash, render_template, request, redirect, url_for, session, json, jsonify
import hashlib
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import datetime
import os
import time

# from dotenv import load_dotenv



app = Flask(__name__)

#секретный ключ
app.secret_key = 'YpUVMwmR8SkqwM'

#соединение с БД
app.config['MYSQL_HOST'] = 'grafvadim.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER'] = 'grafvadim'
app.config['MYSQL_PASSWORD'] = '2qiwH7MLrTHPijF'
app.config['MYSQL_DB'] = 'grafvadim$test'

#инициализация mysql
mysql = MySQL(app)

# временная зона для приложения
# os.environ["TZ"] = "Europe/Moscow"
# time.tzset()

@app.route('/', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST' and 'login' in request.form and 'password' in request.form:
        auth = request.form
        login = auth.get('login')
        password=auth.get('password')
        passw = password.encode()
        h = hashlib.md5()
        h.update(passw)
        hashpassw = str(h.hexdigest())
        cursor = mysql.connection.cursor()
        cursor.execute("""SELECT *, group_concat(sName, concat(left(fName,1),'.'),
                concat(left(patr,1),'.')) as fio
                FROM user JOIN user_role
                ON user.role_id=user_role.id
                join user_post ON user.post_id=user_post.id
                WHERE login = %s and pass=%s
                GROUP BY user.id
                ORDER BY user.id""", (login, hashpassw))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account[0]
            session['login'] = account[1]
            session['user_role_id'] = account[8]
            session['user_post_id'] = account[11]
            session['user_role'] = account[13]
            session['user_post'] = account[15]
            session['user_fio'] = account[16]

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('insert into logs(user_id, time, ip_address, action) values(%s, %s, %s, "Вход в приложение")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], ))
            mysql.connection.commit()
            return redirect(url_for('main'))
    return render_template('login.html')



#выйти из приложения, редирект на Вход
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('login', None)
    session.pop('user_role_id', None)
    session.pop('user_fio', None)
    return redirect(url_for('login'))


@app.route('/register-user')
def get_data_for_reg_user():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, title as city FROM city')
    cities = cursor.fetchall()
    cursor.execute('SELECT id, title as post FROM user_post')
    posts = cursor.fetchall()
    cursor.execute('SELECT id, title as role FROM user_role')
    roles = cursor.fetchall()
    return render_template('add_user.html', cities=cities, posts=posts, roles=roles)


#страница регистрации пользователя
@app.route('/register-user', methods = ['GET', 'POST'])
def register():
    register = request.form
    # если введены все данные
    # в поля формы регистрации пользователя
    if request.method == 'POST' and register:
        login = register.get('login')
        password = register.get('password')
        sname = register.get('sname')
        fname = register.get('fname')
        patr = register.get('patr')
        city = register.get('cities')
        phone = register.get('phone')
        post = register.get('posts')
        role = register.get('roles')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        #запрос в бд для записи данных нового пользователя
        cursor.execute("""INSERT INTO user(login, pass, sName, fName,
                            patr, city_id, phone_number, post_id, role_id)
                            VALUES (%s, md5(%s), %s, %s,
                                %s, %s, %s, %s, %s)""",
            (login, password, sname, fname, patr, city, phone, post, role))
        account = cursor.fetchone()
        #проверить, существует ли уже такой аккаунт
        if account:
            flash('Такой аккаунт уже существует!', 'danger')
        elif not re.match(r'[A-Za-z0-9]+', login): #запретить ввод киррилицы
            flash('Логин должен состоять только из латинских букв и цифр.', 'info')
        elif not login or not password or not sname: #если некоторые поля пустые
            flash('Пожалуйста, заполните все поля формы!', 'warning')
        else:

            flash('Регистрация прошла успешно!', 'success')
            cursor.execute('SELECT last_insert_id() as newuser')
            user = cursor.fetchone()
            cursor.execute('insert into logs(user_id, time, ip_address, action) values(%s, %s, %s, "Зарегистрировал пользователя id(%s)")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], user['newuser'], ))
            mysql.connection.commit()
    # если не заполнены все поля формы
    elif request.method == 'POST':
        flash('Пожалуйста, заполните все поля формы!', 'warning')
    return render_template('add_user.html', userrole=session['user_post'],
        userfio=session['user_fio'], userroleid=session['user_role_id'])


#главная страница приложения
# после авторизации
@app.route('/main')
def main():
    #проверить залогинился ли пользователь
    if 'loggedin' in session:
        #если залогинился, перейти на страницу поиска
        return render_template('patient_search.html', userrole=session['user_post'], userfio=session['user_fio'],  userroleid=session['user_role_id'])
    #если не залогинился, перенаправить на страницу логин формы
    return redirect(url_for('login'))



#страница Поиск
@app.route('/search', methods = ['GET', 'POST'])
def search_patient():
    if 'loggedin' in session:
        if request.method == "POST" and request.form:
            sname = request.form['sname'] #фамилия, полученная из поля формы на странице
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # поиск пациента по имени или фамилии
            cursor.execute("""SELECT * FROM pacient WHERE sName=%s""", (sname,))
            mysql.connection.commit()
            patients = cursor.fetchall() # сохранить полученные данные в переменной patients
            if len(patients) == 0:
                flash('По вашему запросу ничего не найдено','info')
            return render_template('patient_search.html', patients=patients,  userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id']) #вернуть полученные данные в шаблон страницы поиска
    return render_template('patient_search.html', userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


@app.route('/search-recipe', methods = ['GET', 'POST'])
def search_recipe():
    if 'loggedin' in session:
        if request.method == "POST" and request.form:
            rec = request.form['rec'] #фамилия, полученная из поля формы на странице
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # поиск пациента по имени или фамилии
            cursor.execute("""SELECT pacient.id as pacient_id, pacient.sName, pacient.fName, pacient.patr,
            recipe.id
            FROM recipe JOIN pacient
            on recipe.pacient_id=pacient.id
            WHERE recipe.id=%s""", (rec,))
            mysql.connection.commit()
            recipes = cursor.fetchall() # сохранить полученные данные в переменной
            if len(recipes) == 0:
                flash('По вашему запросу ничего не найдено','info')
            return render_template('recipe_search.html', recipes=recipes,  userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id']) #вернуть полученные данные в шаблон страницы поиска
    return render_template('recipe_search.html', userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])



# patient_register.html
@app.route('/register-patient')
def select():
    """Возвращает данные для выпадающих списков на форме регистрации пациента"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #запрос данных о пол
    cursor.execute('SELECT id, title FROM gender')
    gender = cursor.fetchall()  #и сохранить в переменную gender
    return render_template('patient_register.html', gender=gender) #вернуть полученные данные в шаблон html


# patient_register.html
@app.route('/register-patient', methods=['GET', 'POST'])
def patientreg():
    reg = request.form
    if 'loggedin' in session and request.method == "POST" and reg:
        sname = reg['sname']
        fname = reg['fname']
        patr = reg['patr']
        age = reg['age']
        datebirth = datetime.datetime.strptime(reg['datebirth'], '%Y-%m-%d')
        datereg = datetime.datetime.strptime(reg['datereg'], '%Y-%m-%d')
        gender = reg.get('gender')
        phone = reg['phone']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" INSERT INTO pacient(sName, fName, patr, datebirth, age, datereg, gender_id, phone, Visits)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""", (sname, fname, patr, datebirth, age, datereg, gender, phone,))
        cursor.execute('SELECT last_insert_id() as patID')
        pat = cursor.fetchone()
        flash('Регистрация прошла успешно.', 'success')
        mysql.connection.commit()
        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, action) values(%s, now(), %s, %s, "Зарегистрировал пациента")',
                        (session['id'], request.headers['X-Real-IP'], pat['patID'] ))
        mysql.connection.commit()
        return redirect(url_for('patient_data', pat_id=pat['patID']))
    elif request.method == "POST":
        flash('Пожалуйста, заполните форму!', 'warning')
    return render_template('patient_register.html')


def get_pat_ID(pat_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" SELECT *,
                        group_concat(sName, concat(left(fName,1),'.'),
                        concat(left(patr,1),'.')) as fio
                    FROM pacient
                    WHERE id=%s
                    GROUP BY id
                    ORDER BY id """, (pat_id,))
    patient = cursor.fetchone()
    return patient


def get_recipe_ID(recID):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT * FROM recipe
                    WHERE id = %s
                    ORDER by id""",(recID,))
    recipes = cursor.fetchone()
    return recipes


# patient_data.html
@app.route('/data/<int:pat_id>', methods=['GET', 'POST'])
def patient_data(pat_id):
    # данные о пациенте по его айди
    patient = get_pat_ID(pat_id)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # запрос к базе для получения данных о выписанных рецептах для конкретного айди пациента
    cursor.execute(""" SELECT recipe.id, recipe.pacient_id, recipe.createDate,
                        recipe.category_id AS rec_cat_id, recipe.price AS rec_price,
                        recipe_category.title AS rec_category,
                        diagnos.title AS diagnos,
                        recipe_status.title AS rec_status
                    FROM recipe
                        JOIN recipe_category ON recipe.category_id = recipe_category.id
                        JOIN diagnos ON recipe.diag_id = diagnos.id
                        JOIN recipe_status ON recipe.status_id = recipe_status.id
                    WHERE recipe.pacient_id = %s
                    ORDER BY recipe.id """, (pat_id,))
    recipes = cursor.fetchall()
    return render_template('patient_data.html',
            patient=patient, recipes=recipes, userroleid=session['user_role_id'])


#patient_data_edit.html
@app.route('/data/<int:pat_id>/edit', methods=['GET', 'POST'])
def patdata_edit(pat_id):
    patient = get_pat_ID(pat_id)
    if request.method == 'POST':
        sname = request.form['sname']
        fname = request.form['fname']
        patr = request.form['patr']
        phone = request.form['phone']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""UPDATE pacient SET sName=%s, fName=%s, patr=%s,
        phone=%s WHERE id=%s""",
        (sname, fname, patr, phone, pat_id))
        flash('Данные пациента изменены.', 'success')
        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, action) values(%s, %s, %s, %s, "Изменил данные пациента")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, ))
        mysql.connection.commit()
        return redirect(url_for('patient_data', pat_id=patient['id'], ))
    return render_template('patient_data_edit.html', patient=patient, userroleid=session['user_role_id'])


# @app.route('/<int:pat_id>/addrecipe/', methods=['GET', 'POST'])
# def add_recipe(pat_id):
#     patient = get_pat_ID(pat_id)
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute('SELECT id, title as diagnos FROM diagnos')
#     diagnosList = cursor.fetchall()
#     cursor.execute('SELECT id as rec_id, title as rec_cat FROM recipe_category')
#     recCat = cursor.fetchall()
#     cursor.execute(""" SELECT id, title as drugCat
#                         from drug_category
#                         where drug_category.title not like '%набор%' """)
#     drugCat = cursor.fetchall()
#     cursor.execute(""" SELECT drug.id as drug_id, drug.ingridient, drug.title as drugname, drug.country,
#             drug.manufacturer, drug_category.id as drCatid, drug_category.title as Drug_category, drug.price
#             FROM drug JOIN drug_category
#             ON drug.category_id=drug_category.id
#             ORDER by drug.id""")
#     selectDrugList = cursor.fetchall()
#     if request.method == 'POST' and session['user_role_id'] == 1 or session['user_role_id'] == 7 or session['user_role_id'] ==3 and request.form:
#         doctor_id = session['id']
#         createDate = datetime.datetime.today()
#         category = int(request.form.get('recCatlist'))
#         diagnos = request.form.get('diagnoslist')
#         price = int(request.form['price'])
#         # count_drug = int(request.form.get('count_drug'))
#         status = 1
#         drugs = request.form.getlist('selectDrugList')
#         cursor.execute(""" select *, count(recipe.pacient_id) as count,
#                             sum(recipe.price) as sumprice
#                         from recipe
#                         join pacient
#                         on recipe.pacient_id=pacient.id
#                         group by recipe.pacient_id
#                         having recipe.pacient_id=%s and recipe.doctor_id=%s and recipe.category_id=%s""", (pat_id, doctor_id, category,))
#         totalrecipes = cursor.fetchall()
#         cursor.execute("""SELECT id, doctor_id, category_id, indicator_limit, indicator_used, indicator_sum
#                 FROM limits where doctor_id=%s and category_id=%s""",(doctor_id, category))
#         limit = cursor.fetchall()
#         if len(totalrecipes) == 0:
#             cursor.execute('update pacient set Visits=1 where id=%s', (pat_id,))
#         if len(limit)==0:
#             cursor.execute("""INSERT INTO limits(doctor_id, category_id, indicator_limit, indicator_used, indicator_sum)
#                         VALUES (%s, %s,10,0,0) """, (doctor_id, category,))
#         if len(limit) !=0 and limit[0]['indicator_used'] == limit[0]['indicator_limit']:
#             flash('Превышен лимит выписки рецепта в данной категории. Обратитесь к администратору.', 'danger')
#         else:
#             cursor.execute(""" UPDATE limits SET indicator_used=indicator_used+1, indicator_sum=indicator_sum+1
#             WHERE doctor_id=%s and category_id=%s """, (doctor_id, category))
#             if len(totalrecipes) == 0:
#                 cursor.execute(""" INSERT INTO
#                                     recipe(pacient_id, doctor_id, createDate, category_id,
#                                     diag_id, status_id, price)
#                                 VALUES (%s,%s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
#                                                                     category, diagnos, status, price))
#                 mysql.connection.commit()
#                 cursor.execute('SELECT last_insert_id() as recipeID')
#                 recipe_id = cursor.fetchone()
#                 for drug in drugs:
#                     cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id) VALUES(%s,%s)',(recipe_id['recipeID'], drug,))
#                 cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
#                     (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
#                 mysql.connection.commit()
#                 flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
#                 return redirect(url_for('patient_data', pat_id=patient['id'],))
#             if len(totalrecipes) != 0:
#                 sumprice = int(totalrecipes[0]['sumprice'])
#                 reccat = int(totalrecipes[0]['category_id'])
#                 if reccat == 1 or reccat == 2:
#                     balance = 1850 - sumprice
#                     vis = int(totalrecipes[0]['Visits']) + 1
#                     if balance < price:
#                         flash('Это посещение: ' +str(vis) +'.' + '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
#                         return render_template('patient_add_recipe.html', patient=patient,diagnosList=diagnosList,
#                                 recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, userroleid=session['user_role_id'])
#                     else:
#                         cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
#                         cursor.execute(""" INSERT INTO
#                                         recipe(pacient_id, doctor_id, createDate, category_id,
#                                         diag_id, status_id, price)
#                                     VALUES (%s,%s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
#                                                                         category, diagnos, status, price))
#                         mysql.connection.commit()
#                         cursor.execute('SELECT last_insert_id() as recipeID')
#                         recipe_id = cursor.fetchone()
#                         for drug in drugs:
#                             cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id) VALUES(%s,%s)',(recipe_id['recipeID'], drug,))
#                         cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
#                             (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
#                         mysql.connection.commit()
#                         flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
#                         return redirect(url_for('patient_data', pat_id=patient['id'],))
#                 elif reccat == 6:
#                     balance = 1500 - sumprice
#                     vis = int(totalrecipes[0]['Visits']) + 1
#                     if balance < price:
#                         flash('Это посещение: ' +str(vis) +'.'+ '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
#                         return render_template('patient_add_recipe.html', patient=patient,diagnosList=diagnosList,
#                             recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, userroleid=session['user_role_id'])
#                     else:
#                         cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
#                         cursor.execute(""" INSERT INTO
#                                         recipe(pacient_id, doctor_id, createDate, category_id,
#                                         diag_id, status_id, price)
#                                     VALUES (%s,%s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
#                                                                         category, diagnos, status, price))
#                         mysql.connection.commit()
#                         cursor.execute('SELECT last_insert_id() as recipeID')
#                         recipe_id = cursor.fetchone()
#                         for drug in drugs:
#                             cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id) VALUES(%s,%s)',(recipe_id['recipeID'], drug,))
#                         cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
#                             (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
#                         mysql.connection.commit()
#                         flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
#                         return redirect(url_for('patient_data', pat_id=patient['id'],))
#                 else:
#                     cursor.execute(""" INSERT INTO
#                                         recipe(pacient_id, doctor_id, createDate, category_id,
#                                         diag_id, status_id, price)
#                                     VALUES (%s,%s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
#                                                                         category, diagnos, status, price))
#                     mysql.connection.commit()
#                     cursor.execute('SELECT last_insert_id() as recipeID')
#                     recipe_id = cursor.fetchone()
#                     for drug in drugs:
#                         cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id) VALUES(%s,%s)',(recipe_id['recipeID'], drug,))
#                     cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
#                         (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
#                     mysql.connection.commit()
#                     flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
#                     return redirect(url_for('patient_data', pat_id=patient['id'],))
#     return render_template('patient_add_recipe.html', patient=patient,diagnosList=diagnosList,
#             recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, userroleid=session['user_role_id'])


@app.route('/<int:pat_id>/add', methods=['GET', 'POST'])
def add(pat_id):
    patient = get_pat_ID(pat_id)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, title as diagnos FROM diagnos')
    diagnosList = cursor.fetchall()
    cursor.execute('SELECT id as rec_id, title as rec_cat FROM recipe_category')
    recCat = cursor.fetchall()
    cursor.execute(""" SELECT id, title as drug_cat
                        from drug_category
                        where drug_category.title not like '%набор%' """)
    drugCat = cursor.fetchall()
    cursor.execute(""" SELECT drug.id as drug_id, drug.ingridient, drug.title as drugname, drug.country,
            drug.manufacturer, drug_category.id as drCatid, drug_category.title as Drug_category, drug.price
            FROM drug JOIN drug_category
            ON drug.category_id=drug_category.id
            ORDER by drug.id""")
    selectDrugList = cursor.fetchall()
    if request.method == 'POST' and request.form:
        doctor_id = session['id']
        createDate = datetime.datetime.today()
        category = int(request.form.get('recCatlist'))
        diagnos = request.form.get('diagnoslist')
        price = int(request.form['price'])
        count_drug = request.form.getlist('qnty')
        status = 1
        drugs = request.form.getlist('chck')
        cursor.execute(""" select *, count(recipe.pacient_id) as count,
                            sum(recipe.price) as sumprice
                        from recipe
                        join pacient
                        on recipe.pacient_id=pacient.id
                        group by recipe.pacient_id
                        having recipe.pacient_id=%s and recipe.doctor_id=%s and recipe.category_id=%s""", (pat_id, doctor_id, category,))
        totalrecipes = cursor.fetchall()
        cursor.execute("""SELECT id, doctor_id, category_id, indicator_limit, indicator_used, indicator_sum
                FROM limits where doctor_id=%s and category_id=%s""",(doctor_id, category))
        limit = cursor.fetchall()
        visit = 1
        res = []
        for count in count_drug:
            if count != '0':
                res.append(count)
        drugList = zip(drugs, res)
        if len(totalrecipes) == 0:
            cursor.execute('update pacient set Visits=1 where id=%s', (pat_id,))
        if len(limit)==0:
            cursor.execute("""INSERT INTO limits(doctor_id, category_id, indicator_limit, indicator_used, indicator_sum)
                        VALUES (%s, %s,10,0,0) """, (doctor_id, category,))
        if len(limit) !=0 and limit[0]['indicator_used'] == limit[0]['indicator_limit']:
            flash('Превышен лимит выписки рецепта в данной категории. Обратитесь к администратору.', 'danger')
        else:
            cursor.execute(""" UPDATE limits SET indicator_used=indicator_used+1, indicator_sum=indicator_sum+1
            WHERE doctor_id=%s and category_id=%s """, (doctor_id, category))
            if len(totalrecipes) == 0:
                cursor.execute(""" INSERT INTO
                                    recipe(pacient_id, doctor_id, createDate, category_id,
                                    diag_id, status_id, price, visit)
                                VALUES (%s,%s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                    category, diagnos, status, price, visit))
                mysql.connection.commit()
                cursor.execute('SELECT last_insert_id() as recipeID')
                recipe_id = cursor.fetchone()
                for drug, i in drugList:
                    cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s,%s)',(recipe_id['recipeID'], drug,i))
                cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
                    (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
                mysql.connection.commit()
                flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                return redirect(url_for('patient_data', pat_id=patient['id'],))
            else:
                sumprice = int(totalrecipes[0]['sumprice'])
                reccat = int(totalrecipes[0]['category_id'])
                if reccat == 1 or reccat == 2:
                    balance = 1850 - sumprice
                    vis = int(totalrecipes[0]['Visits']) + 1
                    if balance < price:
                        flash('Это посещение: ' +str(vis) +'.' + '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
                        return render_template('test.html', patient=patient,diagnosList=diagnosList,
                                recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, userroleid=session['user_role_id'])
                    else:
                        cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
                        cursor.execute(""" INSERT INTO
                                        recipe(pacient_id, doctor_id, createDate, category_id,
                                        diag_id, status_id, price, visit)
                                    VALUES (%s,%s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                        category, diagnos, status, price, vis))
                        mysql.connection.commit()
                        cursor.execute('SELECT last_insert_id() as recipeID')
                        recipe_id = cursor.fetchone()
                        for drug, i in drugList:
                            cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s,%s)',(recipe_id['recipeID'], drug,i))
                        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
                            (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
                        mysql.connection.commit()
                        flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                        return redirect(url_for('patient_data', pat_id=patient['id'],))
                elif reccat == 6:
                    balance = 1500 - sumprice
                    vis = int(totalrecipes[0]['Visits']) + 1
                    if balance < price:
                      flash('Это посещение: ' +str(vis) +'.'+ '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
                      return render_template('test.html', patient=patient,diagnosList=diagnosList,
                            recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, userroleid=session['user_role_id'])
                    else:
                        cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
                        cursor.execute(""" INSERT INTO
                                        recipe(pacient_id, doctor_id, createDate, category_id,
                                        diag_id, status_id, price, visit)
                                    VALUES (%s,%s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                        category, diagnos, status, price, vis))
                        mysql.connection.commit()
                        cursor.execute('SELECT last_insert_id() as recipeID')
                        recipe_id = cursor.fetchone()
                        for l in drugList:
                            drug, i = l
                            if len(l) !=2:
                                cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s, %s)',(recipe_id['recipeID'], drugs, res))
                            else:
                                cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s, %s)',(recipe_id['recipeID'], drug, i))
                        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
                            (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
                        mysql.connection.commit()
                        flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                        return redirect(url_for('patient_data', pat_id=patient['id'],))
                else:
                    cursor.execute(""" INSERT INTO
                                        recipe(pacient_id, doctor_id, createDate, category_id,
                                        diag_id, status_id, price)
                                    VALUES (%s,%s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                        category, diagnos, status, price))
                    mysql.connection.commit()
                    cursor.execute('SELECT last_insert_id() as recipeID')
                    recipe_id = cursor.fetchone()
                    for l in drugList:
                        drug, i = l
                        if len(l) !=2:
                            cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s, %s)',(recipe_id['recipeID'], drugs, res))
                        else:
                            cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s, %s)',(recipe_id['recipeID'], drug, i))
                    cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id, recipe_id['recipeID'],))
                    mysql.connection.commit()
                    flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                    return redirect(url_for('patient_data', pat_id=patient['id'],))
    return render_template('test.html', patient=patient,diagnosList=diagnosList,
            recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, userroleid=session['user_role_id'])


@app.route('/recipeinfo/<int:recID>', methods=['GET', 'POST'])
def recipe_info(recID):
    recipes = get_recipe_ID(recID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT recipe.id, recipe.pacient_id,
                        recipe.doctor_id as doctor_id,
                        recipe.pharm_id as pharm_id, recipe.createDate,
                        recipe.category_id AS rec_cat_id, recipe.price AS rec_price,
                        recipe_category.title AS rec_category,
                        recipe.diag_id as diag_id,
                        diagnos.title AS diagnos, recipe.status_id,
                        recipe_status.title AS rec_status,
                        pacient.sName as pat_sname, pacient.fName as pat_fname, pacient.patr as pat_patr,
                        pacient.datebirth as pat_datebirth, pacient.phone as pat_phone,
                        pacient.passport, pacient.inn, pacient.parentinn,
                        pacient.PlaceActualResidence,
                        user.id as userid, user.sName as doctor_sname,
                        user.fName as doctor_fname,
                        user.patr as doctor_patr, user_post.title as doctor_post,
                        city.title as city
                    FROM recipe
                        JOIN recipe_category ON recipe.category_id = recipe_category.id
                        JOIN diagnos ON recipe.diag_id = diagnos.id
                        JOIN recipe_status ON recipe.status_id = recipe_status.id
                        JOIN pacient ON recipe.pacient_id = pacient.id
                        JOIN user ON recipe.doctor_id = user.id
                        JOIN user_post ON user.post_id=user_post.id
                        JOIN city on user.city_id=city.id
                    WHERE recipe.id = %s
                    ORDER BY recipe.id""",(recID,))
    recipeinfo = cursor.fetchone()
    cursor.execute(""" select recipe.id, recipe.pharm_id, recipe.endDate, user.sName, user.fName, user.patr,
                        recipe.status_id, city.title as city
                        from recipe join user on recipe.pharm_id = user.id
                        join city on user.city_id=city.id
                        where recipe.id = %s""", (recID,))
    pharminfo = cursor.fetchone()
    recID = recipeinfo['id']
    cursor.execute(""" SELECT drug.title as drug_name, drug.ingridient, drug.country,
                drug.manufacturer, drug.price as drug_price,
                crosstrecdrug.rec_id, crosstrecdrug.drug_id, crosstrecdrug.count
                FROM drug
                JOIN crosstrecdrug ON drug.id = crosstrecdrug.drug_id WHERE crosstrecdrug.rec_id=%s""", (recID,))
    recDrugs = cursor.fetchall()
    if request.method == 'POST':
        pharm_id = session['id']
        endDate = datetime.datetime.today()
        status = 2
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE recipe SET pharm_id=%s, endDate=%s, status_id=%s WHERE id=%s', (pharm_id, endDate, status, recID,))
        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Отпустил рецепт")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], recipeinfo['pacient_id'], recID,))
        mysql.connection.commit()
        flash('Рецепт отпущен. Код рецепта: ' + str(recID), 'success')
    return render_template('releaserecipe.html', recipes=recipes, recipeinfo=recipeinfo, pharminfo=pharminfo, recDrugs=recDrugs,
            userroleid=session['user_role_id'], userfio=session['user_fio'])


@app.route('/<int:pat_id>/add-data', methods=['GET', 'POST'])
def add_identific_data(pat_id):
    patient = get_pat_ID(pat_id)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method=='POST' and request.form:
        passport = request.form.get('passport')
        inn = request.form.get('inn')
        parentinn = request.form.get('parentinn')
        address = request.form.get('address')
        cursor.execute(""" update pacient
                            set passport=%s, inn=%s, parentinn=%s, PlaceActualResidence=%s
                            where id = %s""", (passport, inn, parentinn, address, pat_id,))
        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, action) values(%s, %s, %s, %s, "Добавил идентиф.данные пациента")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], pat_id,))
        mysql.connection.commit()
        flash('Идентификационные данные успешно добавлены.', 'success')
        return redirect(url_for('patient_data', pat_id=patient['id']))
    return render_template('add_identific_data.html', patient=patient)


def get_drug_ID(drugID):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" SELECT * FROM drug
                        WHERE drug.id=%s
                        ORDER BY drug.id """, (drugID,))
    druginfo = cursor.fetchone()
    return druginfo


def get_user_limits(limitID):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT id, doctor_id, category_id, indicator_limit, indicator_used, indicator_sum
                FROM limits where id=%s
                order by id """,(limitID,))
    limituser = cursor.fetchall()
    return limituser


@app.route('/limits', methods = ['GET', 'POST'])
def limits():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" select limits.id, limits.doctor_id, limits.category_id,
                        limits.indicator_limit, limits.indicator_used, limits.indicator_sum,
                        user.sName, user.fName, user.patr, user.phone_number as phone,
                        recipe_category.title as rec_category,
                        recipe_category.id as recCatid,
                        user_post.title as user_post
                        from limits
                        join user on limits.doctor_id=user.id
                        join recipe_category on limits.category_id=recipe_category.id
                        join user_post on user.post_id=user_post.id""")
    limits = cursor.fetchall()
    return render_template('limits.html', limits=limits, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


@app.route('/limits/<int:limitID>/edit', methods = ['GET', 'POST'])
def edit_limit(limitID):
    limituser =  get_user_limits(limitID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" select limits.id, limits.doctor_id, limits.category_id,
                        limits.indicator_limit, limits.indicator_used, limits.indicator_sum,
                        user.sName, user.fName, user.patr, user.phone_number as phone,
                        recipe_category.title as rec_category,
                        recipe_category.id as recCatid,
                        user_post.title as user_post
                        from limits
                        join user on limits.doctor_id=user.id
                        join recipe_category on limits.category_id=recipe_category.id
                        join user_post on user.post_id=user_post.id
                        where limits.id=%s""", (limitID,))
    limituser=cursor.fetchone()
    if request.method == 'POST':
        indicator_limit = request.form.get('indicator_limit')
        cursor.execute(""" UPDATE limits SET indicator_limit=%s, indicator_used=0
                WHERE id=%s """, (indicator_limit, limitID))
        mysql.connection.commit()
        flash('Изменения сохранены','success')
        return redirect(url_for('limits'))
    return render_template('limit_user_edit.html', limituser=limituser, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


# patient_drugs.html
@app.route('/drugs', methods = ['GET', 'POST'])
def drugs():
    """ Возвращает данные о всех имеющихся препаратах """
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" SELECT drug.id, drug.ingridient, drug.title as drug_title, drug.country,
                drug.manufacturer, drug_category.id as drCatid, drug_category.title as Drug_category, drug.price
                FROM drug JOIN drug_category
                ON drug.category_id=drug_category.id
                order by drug.id""")
        mysql.connection.commit()
        drugs=cursor.fetchall()
        return render_template('patient_drugs.html', drugs=drugs, userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id']) #вернуть полученные данные в шаблон страницы препаратов


@app.route('/add-drug')
def select2():
    """Возвращает данные для выпадающих списков на форме """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, title AS drcategory FROM drug_category')
    drugCat = cursor.fetchall()
    return render_template('patient_add_drug.html', drugCat=drugCat)


@app.route('/add-drug', methods=['GET', 'POST'])
def add_drug():
    reg = request.form
    if request.method == "POST":
        ingridient = reg.get('ingridient')
        drug_title = reg.get('drug_title')
        country = reg.get('drug_country')
        manufacturer = reg.get('manufacturer')
        drugCat = reg.get('drugCat')
        price = reg.get('price')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" INSERT INTO drug(ingridient, title, country,
                                manufacturer, category_id, price)
                            VALUES (%s, %s, %s, %s, %s, %s) """, (ingridient, drug_title,
                            country, manufacturer, drugCat, price,))
        cursor.execute('SELECT last_insert_id() as newdrug')
        drug = cursor.fetchone()
        cursor.execute('insert into logs(user_id, time, ip_address, drug_id, action) values(%s, %s, %s, %s, "Добавил препарат")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], drug['newdrug']))
        mysql.connection.commit()
        flash('Препарат добавлен.', 'success')
        return redirect(url_for('drugs'))
    else:
        flash('ошибка', 'danger')
    return render_template('patient_add_drug.html', userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


@app.route('/drugs/<int:drugID>/edit', methods=['GET', 'POST'])
def edit_drug(drugID):
    druginfo = get_drug_ID(drugID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        ingridient = request.form.get('ingridient')
        drug_title = request.form.get('drug_title')
        country = request.form.get('drug_country')
        manufacturer = request.form.get('manufacturer')
        price = request.form.get('price')
        cursor.execute(""" UPDATE drug SET ingridient=%s, title=%s, country=%s,
                            manufacturer=%s, price=%s  where id=%s""", (ingridient, drug_title,
                                country, manufacturer, price, drugID))
        cursor.execute('insert into logs(user_id, time, ip_address, drug_id, action) values(%s, %s, %s, %s, "Изменил данные о препарате")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], drugID,))
        mysql.connection.commit()
        flash('Информация о препарате успешно изменена', 'success')
        return redirect(url_for('drugs'))
    return render_template('patient_drug_edit.html', druginfo=druginfo, userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


@app.route('/drugs/<int:drugID>/delete', methods=['GET', 'POST'])
def delete_drug(drugID):
    druginfo = get_drug_ID(drugID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('DELETE FROM drug WHERE id=%s', (drugID,))
        cursor.execute('insert into logs(user_id, time, ip_address, drug_id, action) values(%s, %s, %s, %s, "Удалил препарат")',
                        (session['id'], datetime.datetime.today(), request.headers['X-Real-IP'], drugID,))
        mysql.connection.commit()
        flash('Препарат удален.', 'success')
        return redirect(url_for('drugs'))
    return render_template('delete_drug.html', druginfo=druginfo,)


# страница с информацией о выданных рецептах фармацевтами по городам
@app.route('/rel-recipes', methods=['GET','POST'])
def rel_recipes():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" SELECT recipe.id, recipe.pacient_id, recipe.category_id, recipe.pharm_id,
                            recipe.endDate, recipe.price, recipe.status_id,
                            pacient.sName as pat_sname, pacient.fName as pat_fname,
                            pacient.patr as pat_patr,
                            user.sName as pharm_sname, user.fName as pharm_fname,
                            user.patr as pharm_patr, user.city_id,
                            recipe_category.title as rec_cat,
                            recipe_status.title as rec_stat,
                            city.title as city
                            FROM recipe
                            JOIN pacient ON recipe.pacient_id=pacient.id
                            JOIN user ON recipe.pharm_id=user.id
                            JOIN recipe_category ON recipe.category_id=recipe_category.id
                            JOIN recipe_status ON recipe.status_id=recipe_status.id
                            JOIN city ON user.city_id=city.id
                            order by recipe.endDate ASC """)
        relRecipes = cursor.fetchall()
    return render_template('release_recipes.html', relRecipes=relRecipes, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


# страница с информацией о выписанных рецептах врачами
@app.route('/written-recipes', methods=['GET','POST'])
def written_recipes():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" SELECT recipe.id, recipe.pacient_id, recipe.category_id, recipe.pharm_id,
                            recipe.createDate, recipe.price, recipe.status_id,
                            pacient.sName as pat_sname, pacient.fName as pat_fname,
                            pacient.patr as pat_patr,
                            user.sName as doctor_sname, user.fName as doctor_fname,
                            user.patr as doctor_patr, user.city_id,
                            recipe_category.title as rec_cat,
                            recipe_status.title as rec_stat,
                            city.title as city
                            FROM recipe
                            JOIN pacient ON recipe.pacient_id=pacient.id
                            JOIN user ON recipe.doctor_id=user.id
                            JOIN recipe_category ON recipe.category_id=recipe_category.id
                            JOIN recipe_status ON recipe.status_id=recipe_status.id
                            JOIN city ON user.city_id=city.id
                            order by recipe.createDate ASC """)
        wrtRecipes = cursor.fetchall()
    return render_template('written_recipes.html', wrtRecipes=wrtRecipes, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])



@app.route('/get-report')
def get_data_for_report():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, title as recCat FROM recipe_category')
    rec_cat = cursor.fetchall()
    cursor.execute('SELECT id, title as gender FROM gender')
    gender = cursor.fetchall()
    cursor.execute('SELECT id, title as diagnos FROM diagnos')
    diagnos = cursor.fetchall()
    cursor.execute('SELECT id, title as city FROM city')
    cities = cursor.fetchall()
    cursor.execute('SELECT id, ingridient FROM drug')
    drugs = cursor.fetchall()
    cursor.execute('SELECT id, title as status from recipe_status')
    rec_status = cursor.fetchall()
    mysql.connection.commit()
    return render_template('form_for_reports.html', rec_cat=rec_cat, diagnos=diagnos, gender=gender, cities=cities, drugs=drugs, rec_status=rec_status)


#test
@app.route('/data', methods=['GET', 'POST'])
def get_data_report():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" SELECT crosstrecdrug.rec_id,
                recipe.createDate, concat(pacient.sName, ' ', pacient.fName, ' ',
                pacient.patr) as fio, pacient.datebirth, pacient.age,
                pacient.inn, pacient.parentinn, gender.title as gender,
                recipe_category.title as rec_cat, diagnos.title as diagnos,
                group_concat(drug.title, ':', crosstrecdrug.count separator ',') as list_drugs,
                recipe.endDate, city.title as city,
                recipe.price, recipe.visit,
                recipe_status.title as rec_stat
                FROM recipe
                JOIN pacient ON recipe.pacient_id=pacient.id
                JOIN user ON recipe.doctor_id=user.id
                JOIN gender ON pacient.gender_id=gender.id
                JOIN crosstrecdrug on recipe.id=crosstrecdrug.rec_id
                JOIN recipe_category ON recipe.category_id=recipe_category.id
                JOIN recipe_status ON recipe.status_id=recipe_status.id
                JOIN diagnos on recipe.diag_id=diagnos.id
                JOIN drug on drug.id=crosstrecdrug.drug_id
                JOIN city ON user.city_id=city.id
                where (recipe.createDate >= '2021-02-01 00:00:00' and
                    recipe.createDate <= '2021-02-28 23:59:59')
                    and (recipe.endDate >= '2021-02-01 00:00:00' and
                        recipe.endDate <= '2021-02-28 23:59:59')
                    and recipe.price > 0
                group by crosstrecdrug.rec_id """)
    records = cursor.fetchall()
    return render_template('recipes.html', records=records)


@app.route('/report', methods=['GET', 'POST'])
def report():
    return render_template('test2.html')


@app.route('/get-report', methods=['GET', 'POST'])
def get_report():
    if request.method == 'POST' and request.form:
        reg = request.form
        d1 = reg['startWD']
        d2 = d1.replace(d1[10], ' ')
        d3 = reg['endWD']
        d4 = d3.replace(d3[10], ' ')
        date1 = datetime.datetime.strptime(d2, '%Y-%m-%d %H:%M:%S')
        date2 = datetime.datetime.strptime(d4, '%Y-%m-%d %H:%M:%S')
        gender = int(reg.get('gender'))
        age1 = int(reg.get('age1'))
        age2 = int(reg.get('age2'))
        rec_cat = int(reg.get('rec_cat'))
        diagnos = int(reg.get('diagnos'))
        drugs = int(reg.get('drugs'))
        cities = int(reg.get('cities'))
        rec_status = int(reg.get('rec_status'))
        visit = int(reg.get('visit'))
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" SELECT crosstrecdrug.rec_id,
            recipe.createDate, concat(pacient.sName, ' ', pacient.fName, ' ',
            pacient.patr) as fio, pacient.datebirth, pacient.age,
            pacient.inn, pacient.parentinn, gender.title as gender,
            recipe_category.title as rec_cat, diagnos.title as diagnos,
            group_concat(drug.title, ':', crosstrecdrug.count separator ',') as list_drugs,
            recipe.endDate, city.title as city,
            recipe.price, recipe.visit,
            recipe_status.title as rec_stat
            FROM recipe
            JOIN pacient ON recipe.pacient_id=pacient.id
            JOIN user ON recipe.doctor_id=user.id
            JOIN gender ON pacient.gender_id=gender.id
            JOIN crosstrecdrug on recipe.id=crosstrecdrug.rec_id
            JOIN recipe_category ON recipe.category_id=recipe_category.id
            JOIN recipe_status ON recipe.status_id=recipe_status.id
            JOIN diagnos on recipe.diag_id=diagnos.id
            JOIN drug on drug.id=crosstrecdrug.drug_id
            JOIN city ON user.city_id=city.id
            where recipe.createDate >= %s and recipe.createDate <=%s and
                recipe.price > 0 and pacient.gender_id=%s
                and recipe.category_id=%s
                and user.city_id=%s and recipe.status_id=%s
                and recipe.visit=%s and (pacient.age between %s and %s)
                and recipe.diag_id=%s and crosstrecdrug.drug_id like %s
            group by crosstrecdrug.rec_id """, (date1, date2, gender, rec_cat,
                                         cities, rec_status, visit, age1, age2, diagnos,drugs))
        records = cursor.fetchall()
        return render_template('test2.html', records=records)
    return render_template('form_for_reports.html', records=records)



if __name__ == '__main__':
    app.run()

