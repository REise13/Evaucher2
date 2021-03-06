from flask import Flask, flash, render_template, request, redirect, url_for, session, json, jsonify
import hashlib
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import datetime
import os
# import time



app = Flask(__name__)

#секретный ключ
app.secret_key = 'YpUVMwmR8SkqwM'

#соединение с БД
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'YpUVMwmR8)'
app.config['MYSQL_DB'] = 'vaucher2'

#инициализация mysql
mysql = MySQL(app)

# временная зона для приложения
# os.environ["TZ"] = "Europe/Moscow"
# time.tzset()

@app.route('/', methods = ['GET', 'POST'])
def login():
    """ Функция входа в приложение """
    if request.method == 'POST' and request.form:
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
            session['city_id'] = account[10]
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('insert into logs(user_id, time, ip_address, action) values(%s, %s, %s, "Вход в приложение")',
                        (session['id'], datetime.datetime.today(), '127.0.0.1', ))
            mysql.connection.commit()
            return redirect(url_for('main'))
        else:
            flash('Введены неправильный логин и/или пароль.', 'danger')
    return render_template('login.html')



#выйти из приложения, редирект на Вход
@app.route('/logout')
def logout():
    """ Функция для выхода из приложения, очистить сессию пользователя """
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('login', None)
    session.pop('user_role_id', None)
    session.pop('user_fio', None)
    session.pop('user_post', None)
    session.pop('user_post_id', None)
    session.pop('user_role', None)
    session.pop('city_id', None)
    return redirect(url_for('login'))


@app.route('/register-user')
def get_data_for_reg_user():
    """ Возвращает данные для выпадающих списков на форму регистрации пользователя """
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
    """ Функция регистрации пользователя """
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
                        (session['id'], datetime.datetime.today(), '127.0.0.1', user['newuser'], ))
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
    """ Редирект на страницу поиск пациента после успешного прохождения авторизации в приложении """
    #проверить залогинился ли пользователь
    if 'loggedin' in session:
        #если залогинился, перейти на страницу поиска
        return render_template('patient_search.html', userrole=session['user_post'], userfio=session['user_fio'],  userroleid=session['user_role_id'])
    #если не залогинился, перенаправить на страницу логин формы
    return redirect(url_for('login'))


#страница Поиск
@app.route('/search', methods = ['GET', 'POST'])
def search_patient():
    """ Возвращает основные данные о пациенте по фамилии из поля поиска на странице """
    if 'loggedin' in session:
        if request.method == "POST" and request.form:
            sname = request.form['sname'] #фамилия, полученная из поля формы на странице
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            sql_doc = """SELECT pacient.id, pacient.sName, pacient.fName,
                                pacient.patr, pacient.passport, pacient.parentinn,
                                pacient.inn, pacient.phone
                                FROM pacient WHERE sName=%s and flagReg=%s"""
            sql_pharm =  """SELECT pacient.id, pacient.sName, pacient.fName,
                                pacient.patr, pacient.passport, pacient.parentinn,
                                pacient.inn, pacient.phone
                                FROM pacient WHERE sName=%s """
            if session['user_role_id'] in [1,3,9]: # Врач, Оператор_P, д1
                # идентификатор для пациента Врача
                num = 0
                cursor.execute(sql_doc, (sname, num,))
            if session['user_role_id'] in [7,4,8]: # Доктор, Оператор_U, д2
                # идентификатор для пациента Доктора
                num = 1
                cursor.execute(sql_doc, (sname, num,))
            if session['user_role_id'] == 2: # фармацевты
                cursor.execute(sql_pharm, (sname,))
            mysql.connection.commit()
            patients = cursor.fetchall() # сохраняем полученные данные в переменной patients
            if len(patients) == 0:
                flash('По вашему запросу: "'+str(sname)+ '" ничего не найдено','warning')
            return render_template('patient_search.html', patients=patients,  userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id']) #вернуть полученные данные в шаблон страницы поиска
    return render_template('patient_search.html', userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


@app.route('/search-recipe', methods = ['GET', 'POST'])
def search_recipe():
    """ Возвращает основные данные о рецепте по коду рецепта из поля поиска на странице """
    if 'loggedin' in session:
        if request.method == "POST" and request.form:
            rec = request.form['rec'] # код рецепта, полученная из поля формы на странице
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # поиск по коду рецепта
            sql_doc = """SELECT pacient.id as pacient_id, pacient.sName,
            pacient.fName, pacient.patr, recipe.id
            FROM recipe JOIN pacient
            on recipe.pacient_id=pacient.id
            WHERE recipe.id=%s and pacient.flagReg=%s"""
            sql_pharm = """SELECT pacient.id as pacient_id, pacient.sName,
            pacient.fName, pacient.patr, recipe.id
            FROM recipe JOIN pacient
            on recipe.pacient_id=pacient.id
            WHERE recipe.id=%s"""

            if session['user_role_id'] in [1,9]: # Врач, д1
                # идентификатор для пациента Врача
                num = 0
                cursor.execute(sql_doc, (rec, num,))
            if session['user_role_id'] in [7,8]: # Доктор, д2
                # идентификатор для пациента Доктора
                num = 1
                cursor.execute(sql_doc, (rec, num,))
            if session['user_role_id'] in [2, 3, 4]: # фармацевты, Оператор_P, Оператор_U
                cursor.execute(sql_pharm, (rec,))
            mysql.connection.commit()
            recipes = cursor.fetchall() # сохранить полученные данные в переменной
            if len(recipes) == 0:
                flash('По вашему запросу: "'+str(rec)+ '" ничего не найдено','warning')
            return render_template('recipe_search.html', recipes=recipes,  userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id']) #вернуть полученные данные в шаблон страницы поиска
    return render_template('recipe_search.html', userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


# patient_register.html
@app.route('/register-patient', methods=['GET', 'POST'])
def patientreg():
    """ Функция регистрации пациента """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #запрос данных о пол
    cursor.execute('SELECT id, title as gendr FROM gender')
    gender = cursor.fetchall()
    reg = request.form
    if 'loggedin' in session and request.method == "POST" and reg:
        sname = reg['sname']
        sname = sname.replace(" ", "")
        fname = reg['fname']
        fname = fname.replace(" ", "")
        patr = reg['patr']
        patr = patr.replace(" ", "")
        age = reg['age']
        datebirth = datetime.datetime.strptime(reg['datebirth'], '%Y-%m-%d')
        datereg = datetime.datetime.strptime(reg['datereg'], '%Y-%m-%d')
        gender = reg.get('gender')
        phone = reg['phone']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM pacient where sName=%s and fName=%s and patr=%s", (sname, fname, patr,))
        if session['user_role_id'] in [1,3,9]: # Врач, Оператор_P, д1
            # идентификатор для регистрируемого пациента Врачом
            num = 0
        if session['user_role_id'] in [7,4,8]: # Доктор, Оператор_U, д2
            # идентификатор для  регистрируемого пациента Доктором
            num = 1
        patient = cursor.fetchall()
        if patient:
            flash('Пациент с таким ФИО уже существует. Воспользуйтесь вкладкой "Поиск пациента".', 'warning')
            return render_template('patient_register.html', gender=gender)
        else:
            cursor.execute(""" INSERT INTO pacient(sName, fName, patr, datebirth, age, datereg, gender_id, phone, flagReg, Visits)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0)""", (sname, fname, patr, datebirth, age, datereg, gender, phone, num,))
            cursor.execute('SELECT last_insert_id() as patID')
            pat = cursor.fetchone()
            flash('Регистрация прошла успешно.', 'success')
            mysql.connection.commit()
            cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, action) values(%s, now(), %s, %s, "Зарегистрировал пациента")',
                            (session['id'], '127.0.0.1', pat['patID'] ))
            mysql.connection.commit()
            return redirect(url_for('patient_data', pat_id=pat['patID']))
    elif request.method == "POST":
        flash('Пожалуйста, заполните форму!', 'warning')
    return render_template('patient_register.html', gender=gender)


def get_pat_ID(pat_id):
    """ Возвращает данные о пациенте по его айди """
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
    """ Возвращает данные о рецепте по его айди """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT * FROM recipe
                    WHERE id = %s
                    ORDER by id""",(recID,))
    recipes = cursor.fetchone()
    return recipes


# patient_data.html
@app.route('/data/<int:pat_id>', methods=['GET', 'POST'])
def patient_data(pat_id):
    """ Возвращает основные данные о пациенте и данные о выписанных рецептах пациенту по айди """
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
    mysql.connection.commit()
    recipes = cursor.fetchall()
    session['pat_id'] = pat_id
    return render_template('patient_data.html',
            patient=patient, recipes=recipes, userroleid=session['user_role_id'])


#patient_data_edit.html
@app.route('/data/<int:pat_id>/edit', methods=['GET', 'POST'])
def patdata_edit(pat_id):
    """ Выполняет апдейт данных пациента """
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
                        (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, ))
        mysql.connection.commit()
        return redirect(url_for('patient_data', pat_id=patient['id'], ))
    return render_template('patient_data_edit.html', patient=patient, userroleid=session['user_role_id'])


@app.route('/<int:pat_id>/add')
def getdata(pat_id):
    """ Возвращает данные для выпадающих списков на форме выписки рецепта """
    patient = get_pat_ID(pat_id)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if session['user_role_id'] in [1,3,9]: # Врач, Оператор_P, д1
        # идентификатор для пациента Врача
        num = 0
        cursor.execute('SELECT id, title as diagnos FROM diagnos WHERE flagDiag=%s ORDER BY title ASC', (num,))
    if session['user_role_id'] in [7,4,8]: # Доктор, Оператор_U, д2
        num = 1
        # идентификатор для пациента Доктора
        cursor.execute('SELECT id, title as diagnos FROM diagnos WHERE id != 12 ORDER BY title ASC')

    diagnosList = cursor.fetchall()
    cursor.execute('SELECT id as rec_id, title as rec_cat, rel_ind FROM recipe_category WHERE flagCat=%s AND rel_ind=1 ORDER BY title ASC', (num,))
    recCat = cursor.fetchall()
    if session['user_role_id'] in [1,3]:
        cursor.execute(""" SELECT id, title as drug_cat
                            from drug_category
                            where drug_category.title not like '%набор%' and flagCat=0
                            ORDER BY title """)
    if session['user_role_id'] in [4,7]:
       cursor.execute(""" SELECT id, title as drug_cat
                            from drug_category
                            where drug_category.title not like '%набор%'
                            ORDER BY title """)
    drugCat = cursor.fetchall()
    if session['user_role_id'] in [1,3]:
        cursor.execute(""" SELECT drug.id as drug_id, drug.ingridient, drug.title as drugname, drug.country,
                drug.manufacturer, drug_category.id as drCatid, drug_category.title as Drug_category, drug.price
                FROM drug JOIN drug_category
                ON drug.category_id=drug_category.id
                WHERE drug.status_id=1 and (drug.flagDrug=0)
                ORDER by drug.id""")
    if session['user_role_id'] in [4,7]:
       cursor.execute(""" SELECT drug.id as drug_id, drug.ingridient, drug.title as drugname, drug.country,
                drug.manufacturer, drug_category.id as drCatid, drug_category.title as Drug_category, drug.price
                FROM drug JOIN drug_category
                ON drug.category_id=drug_category.id
                WHERE drug.status_id=1
                ORDER by drug.id""")
    selectDrugList = cursor.fetchall()
    cursor.execute(""" select recipe.category_id as rec_id, recipe_category.title as rec_cat, recipe_category.rel_ind
                from recipe
                join recipe_category
                on recipe.category_id=recipe_category.id
                WHERE recipe.pacient_id=%s and recipe_category.rel_ind=2
                     """, (pat_id,))
    patCat = cursor.fetchall()
    patIndCat = tuple()
    patCheck = []
    patnewCat = []
    recCatList = recCat
    if patCat:
        for cat in patCat:
            if cat not in patnewCat:
                patnewCat.append(cat)
        pat = tuple(patnewCat)
        patcats= recCatList + pat
        patIndCat = sorted(patcats, key=lambda x: (x['rec_cat']))
    return render_template('patient_addrecipe.html', patient=patient,diagnosList=diagnosList,
                        recCat=recCat, drugCat=drugCat, selectDrugList=selectDrugList, patIndCat=patIndCat)


@app.route("/get_pat_balance",methods=["POST","GET"])
def get_pat_balance():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        pt_id = int(request.form['pt'])
        ct_id = int(request.form['ct'])

        cursor.execute('select id, sum from money_limit')
        money_limit = cursor.fetchall()

        # array ONE with recipe category id's:
        arr1 = [11, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        # array TWO with recipe category id's:
        arr2 = [13, 15, 17, 19, 21, 23, 25, 27, 29]
        patb_diff = int()

        if ct_id == 6: # 097
            patb_diff = int(money_limit[1]['sum'])
        if ct_id == 1 or ct_id == 2:  # 092 and 093
            patb_diff = int(money_limit[0]['sum'])
        if ct_id in arr1:
            patb_diff = int(money_limit[2]['sum'])
        if ct_id in arr2:
            patb_diff = int(money_limit[3]['sum'])
        if ct_id == 10: # 091
            patb_diff = int(money_limit[4]['sum'])
        if ct_id == 3:  # 094
            patb_diff = int(money_limit[5]['sum'])
        if ct_id == 4: # 095
            patb_diff = int(money_limit[6]['sum'])
        if ct_id == 5: # 096
            patb_diff = int(money_limit[7]['sum'])
        if ct_id == 7: # 098
            patb_diff = int(money_limit[8]['sum'])
        if ct_id == 8: # 099
            patb_diff = int(money_limit[9]['sum'])
        if ct_id == 9: # 100
            patb_diff = int(money_limit[10]['sum'])

        if ct_id in [3,4,5,7,9,10]:
            cursor.execute('SELECT id FROM recipe WHERE pacient_id=%s AND category_id IN(3,4,5,7,9,10)', (pt_id,))
            nabor = cursor.fetchall()
        else:
            nabor = ""
        cursor.execute("select sum(price) AS sum_rec from recipe where pacient_id=%s and recipe.category_id=%s", (pt_id, ct_id,))
        patBal = cursor.fetchall()
        pat_int = ""
        if patBal[0]['sum_rec'] != None:
            if len(nabor) != 0:
                pat_int = -1
            else:
                pat_int = int(patb_diff - int(patBal[0]['sum_rec']))
        else:
            if len(nabor) != 0:
                pat_int = -1
            else:
                pat_int = patb_diff
    return jsonify({'htmlresponse': pat_int})


@app.route("/get_drug_cat",methods=["POST","GET"])
def get_drug_cat():
    if request.method == 'POST':
        dr_ct_id = int(request.form['dr_ct'])

        # array with recipe category id's:
        arr = [13, 15, 17, 19, 21, 23, 25, 27, 29]
        status = ""

        if dr_ct_id in arr:
            status = "Y"
        drug_cat = ""
        if status != "":
            drug_cat = status
    return jsonify({'htmlresponse': drug_cat})


@app.route("/get_user_limit",methods=["POST","GET"])
def get_user_limit():
    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        ct_id = int(request.form['ct_id'])
        print(user_id)
        print(ct_id)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""SELECT indicator_limit, indicator_used
                FROM limits where doctor_id=%s and category_id=%s""",(user_id, ct_id,))
        limit = cursor.fetchall()
        status = ""

        if limit[0]['indicator_used'] == limit[0]['indicator_limit']:
            status = "Y"
        userLimit = ""
        if status != "":
            userLimit = status
    return jsonify({'htmlresponse': userLimit})


@app.route('/<int:pat_id>/add', methods=['GET', 'POST'])
def add(pat_id):
    """ Функция выписки рецепта """
    patient = get_pat_ID(pat_id)
    if request.method == 'POST' and request.form:
        # получаем введенные данные из полей формы
        doctor_id = session['id']
        city = session['city_id']
        createDate = datetime.datetime.today()
        category = int(request.form.get('recCatlist'))
        diagnos = request.form.get('diagnoslist')
        price = int(request.form['price'])
        count_drug = request.form.getlist('qnty')
        status = 1
        drugs = request.form.getlist('chck')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # создаем запрос к базе для получения данных
        # о выписанныхт раннее рецептах пациенту
        # в выбранной категории рецепта
        cursor.execute(""" select *, count(recipe.pacient_id) as count,
                            sum(recipe.price) as sumprice
                        from recipe
                        join pacient
                        on recipe.pacient_id=pacient.id
                        where recipe.pacient_id=%s and recipe.category_id=%s
                        group by recipe.pacient_id
                         """, (pat_id, category,))
        totalrecipes = cursor.fetchall()
        # запрос к базе данных для получения данных
        # о количестве выписанных рецептов в данной категории пользователем
        cursor.execute("""SELECT id, doctor_id, category_id, indicator_limit, indicator_used, indicator_sum
                FROM limits where doctor_id=%s and category_id=%s""",(doctor_id, category))
        limit = cursor.fetchall()
        # запрос к базе для получения данных о выданном наборе пациенту
        cursor.execute('SELECT * FROM recipe WHERE pacient_id=%s AND (category_id=3 OR category_id=4 OR category_id=5 OR category_id=7 OR category_id=10)', (pat_id,))
        nabor = cursor.fetchall()
        # создаем переменную и передаем
        # туда сумму только что выписываемого рецепта
        pat_balance = price
        if category == 1 or category == 2:
            # если выбрана категория 092 или 093,
            # то начальный баланс равен
            pat_balance = 2100
        if category == 6 or category == 8:
            # а если категория 097,
            # то начальный баланс пациента равен
            pat_balance = 1700

        # если катеория 100.1, 100.2, 100.4, 100.6,
        # 100.8, 101.1, 101.3, 101.5, 101.7 или 102.1
        if category in [11, 12, 14, 16, 18, 20, 22, 24, 26, 28]:
            pat_balance = 1960

        # если категория 100.3, 100.5, 100.7,
        # 100.9, 101.2, 101.4, 101.6, 101.8 или 102.2
        if category in [13, 15, 17, 19, 21, 23, 25, 27, 29]:
            pat_balance = 875

        # создаем переменную посещения пациентом данного врача
        # по умолчанию оно равно 1 (первое посещение)
        visit = 1
        res = []
        # проходимся циклом по выбранным препаратам
        # и количеству каждого выбранного препарата
        # и записываем его в список drugList
        for count in count_drug:
            if count != '0':
                res.append(count)
        drugList = zip(drugs, res)
        if len(totalrecipes) == 0:
            # если в данной категории у пациента первое посещение,
            # то обновляем данные в базе
            cursor.execute('update pacient set Visits=1 where id=%s', (pat_id,))
        if len(limit)==0:
            # если пользователь первый раз выписывает рецепт в выбранной категории,
            # то добавляем соответствую запись в лимиты базы;
            # где количество доступных выписок в данной категории равно 10
            cursor.execute("""INSERT INTO limits(doctor_id, category_id, indicator_limit, indicator_used, indicator_sum)
                        VALUES (%s, %s,10,0,0) """, (doctor_id, category,))
        if len(limit) !=0 and limit[0]['indicator_used'] == limit[0]['indicator_limit']:
            # если лимит выписанных рецептов в выбранной категории достигнут,
            # то выводим предупреждение и выписка рецепта невозможна
            flash('Превышен лимит выписки рецепта в данной категории. Обратитесь к администратору.', 'danger')
        else:
            # иначе обновляем индикатор выписки рецептов в данной категории к +1
            cursor.execute(""" UPDATE limits SET indicator_used=indicator_used+1, indicator_sum=indicator_sum+1
            WHERE doctor_id=%s and category_id=%s """, (doctor_id, category))
            if len(totalrecipes) == 0:
                # проверяем выдавался ли ранее набор пациенту и в других категориях,
                # если да, то выводим предупреждение
                # и выписка рецепта невозможна
                if len(nabor) !=0 and category in [3,4,5,7,9,10]:
                    flash('Пациент уже получал набор! \nВы не можете выписать его еще раз!','danger')
                    return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])
                # иначе вносим данные в базу
                cursor.execute(""" INSERT INTO
                                    recipe(pacient_id, doctor_id, createDate, category_id,
                                    diag_id, status_id, price, balance, visit, city_id)
                                VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                    category, diagnos, status, price, pat_balance,  visit, city))
                mysql.connection.commit()
                cursor.execute('SELECT last_insert_id() as recipeID')
                recipe_id = cursor.fetchone()
                # проходимся циклом из словаря препаратов и их количества
                # и вносим полученные данные в базу
                for drug, i in drugList:
                    cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s,%s)',(recipe_id['recipeID'], drug,i))
                cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
                    (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, recipe_id['recipeID'],))
                mysql.connection.commit()
                # выводим сообщение на страницу с информацией
                # об успешной выпиской и кодом данного рецепта
                flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                return redirect(url_for('patient_data', pat_id=patient['id'],))
            else:
                # если пациенту раннее уже был выписан рецепт(-ы) в данной категории,
                # то проверяем ряд условий
                sumprice = int(totalrecipes[0]['sumprice'])
                reccat = int(totalrecipes[0]['category_id'])
                if reccat == 1 or reccat == 2:
                    # не выходит ли сумма выписываемого рецепта
                    # за баланс пользователя в категории 092 или 093
                    balance = 2100 - sumprice
                    vis = int(totalrecipes[0]['count']) + 1
                    # если превышает баланс, то выписка невозможна
                    # и сообщение с предупреждением
                    if balance < price:
                        flash('Это посещение: ' +str(vis) +'.' + '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
                        return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])
                    else:
                        # иначе вносим данные в базу
                        # обновленный баланс пациента
                        b2 = balance
                        # посещение пациента
                        vv = int(totalrecipes[0]['count']) + 1
                        cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
                        cursor.execute(""" INSERT INTO
                                        recipe(pacient_id, doctor_id, createDate, category_id,
                                        diag_id, status_id, price, balance, visit, city_id)
                                    VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                        category, diagnos, status, price, b2, vv, city))
                        mysql.connection.commit()
                        cursor.execute('SELECT last_insert_id() as recipeID')
                        recipe_id = cursor.fetchone()
                        for drug, i in drugList:
                            cursor.execute('INSERT INTO crosstrecdrug(rec_id, drug_id, count) VALUES(%s,%s,%s)',(recipe_id['recipeID'], drug,i))
                        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Выписал рецепт")',
                            (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, recipe_id['recipeID'],))
                        mysql.connection.commit()
                        flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                        return redirect(url_for('patient_data', pat_id=patient['id'],))
                elif reccat == 6 or reccat == 8:
                    # если катеория 097
                    # проверяем баланс также, как при предудущих категориях
                    balance = 1700 - sumprice
                    vis = int(totalrecipes[0]['count']) + 1
                    if balance < price:
                      flash('Это посещение: ' +str(vis) +'.'+ '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
                      return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])
                    else:
                        # если сумма данного рецепта не превышает баланса,
                        # то вносим данные в базу
                        b2 = balance
                        vv = int(totalrecipes[0]['count']) + 1
                        cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
                        cursor.execute(""" INSERT INTO
                                    recipe(pacient_id, doctor_id, createDate, category_id,
                                    diag_id, status_id, price, balance, visit, city_id)
                                VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                    category, diagnos, status, price, b2, vv, city))
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
                            (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, recipe_id['recipeID'],))
                        mysql.connection.commit()
                        flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                        return redirect(url_for('patient_data', pat_id=patient['id'],))
                elif reccat in [11, 12, 14, 16, 18, 20, 22, 24, 26, 28]:
                    # если катеория 100.1, 100.2, 100.4, 100.6,
                    # 100.8, 101.1, 101.3, 101.5, 101.7 или 102.1
                    # проверяем баланс также, как при предудущих категориях
                    balance = 1960 - sumprice
                    vis = int(totalrecipes[0]['count']) + 1
                    if balance < price:
                      flash('Это посещение: ' +str(vis) +'.'+ '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
                      return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])
                    else:
                        # если сумма данного рецепта не превышает баланса,
                        # то вносим данные в базу
                        b2 = balance
                        vv = int(totalrecipes[0]['count']) + 1
                        cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
                        cursor.execute(""" INSERT INTO
                                    recipe(pacient_id, doctor_id, createDate, category_id,
                                    diag_id, status_id, price, balance, visit, city_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                    category, diagnos, status, price, b2, vv, city))
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
                            (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, recipe_id['recipeID'],))
                        mysql.connection.commit()
                        flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                        return redirect(url_for('patient_data', pat_id=patient['id'],))
                elif reccat in [13, 15, 17, 19, 21, 23, 25, 27, 29]:
                    # если категория 100.3, 100.5, 100.7,
                    # 100.9, 101.2, 101.4, 101.6, 101.8 или 102.2
                    # проверяем баланс также, как при предыдущих категориях
                    balance = 875 - sumprice
                    vis = int(totalrecipes[0]['count']) + 1
                    if balance < price:
                      flash('Это посещение: ' +str(vis) +'.'+ '\nСумма выписываемого рецепта превышает остаток на балансе пациента в данной категории.' + '\nОстаток: '+ str(balance)+ ' руб.','danger')
                      return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])
                    else:
                        # если сумма данного рецепта не превышает баланса,
                        # то вносим данные в базу
                        b2 = balance
                        vv = int(totalrecipes[0]['count']) + 1
                        cursor.execute('update pacient set Visits=Visits+1 where id=%s', (pat_id,))
                        cursor.execute(""" INSERT INTO
                                    recipe(pacient_id, doctor_id, createDate, category_id,
                                    diag_id, status_id, price, balance, visit, city_id)
                                VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                    category, diagnos, status, price, b2, vv, city))
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
                            (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, recipe_id['recipeID'],))
                        mysql.connection.commit()
                        flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                        return redirect(url_for('patient_data', pat_id=patient['id'],))
                elif reccat in [3, 4, 5, 7, 10]:
                    # если выбранная категория совпадает с категорией выбанного набора
                    flash('Пациент уже получал набор! \nВы не можете выписать его еще раз!','danger')
                    return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])
                else:
                    # иначе вносим данные в базу
                    vv = int(totalrecipes[0]['count']) + 1
                    cursor.execute(""" INSERT INTO
                                        recipe(pacient_id, doctor_id, createDate, category_id,
                                        diag_id, status_id, price, balance, visit, city_id)
                                    VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (pat_id, doctor_id, createDate,
                                                                        category, diagnos, status, price, price, vv, city))
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
                        (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id, recipe_id['recipeID'],))
                    mysql.connection.commit()
                    flash('Рецепт выписан. Код рецепта: '+ str(recipe_id['recipeID']), 'success')
                    return redirect(url_for('patient_data', pat_id=patient['id'],))
    return render_template('patient_addrecipe.html', patient=patient, userroleid=session['user_role_id'])


@app.route('/recipeinfo/<int:recID>', methods=['GET', 'POST'])
def recipe_info(recID):
    """ Возвращает информацию о выписанном рецепте пациенту на страницу """
    recipes = get_recipe_ID(recID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # запрос о получении данных о выписанном рецепте пациенту
    cursor.execute("""SELECT recipe.id, recipe.pacient_id, recipe.createDate,
                        recipe.category_id AS rec_cat_id, recipe.price AS rec_price,
                        recipe_category.title AS rec_category,
                        diagnos.title AS diagnos, recipe.status_id,
                        recipe_status.title AS rec_status,
                        recipe.balance,
                        recipe.visit,
                        pacient.sName as pat_sname, pacient.fName as pat_fname, pacient.patr as pat_patr,
                        pacient.datebirth as pat_datebirth, pacient.phone as pat_phone,
                        pacient.passport, pacient.inn, pacient.parentinn,
                        pacient.PlaceActualResidence,
                        user.sName as doctor_sname,
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
                        JOIN city on recipe.city_id=city.id
                    WHERE recipe.id = %s
                    ORDER BY recipe.id""",(recID,))
    recipeinfo = cursor.fetchone()
    # запрос о получении информации о фармацевте, который отпустил данный рецепт
    cursor.execute(""" select recipe.endDate, user.sName, user.fName, user.patr,
                        recipe.status_id, city.title as city
                        from recipe join user on recipe.pharm_id = user.id
                        join city on recipe.pharm_city=city.id
                        where recipe.id = %s""", (recID,))
    mysql.connection.commit()
    pharminfo = cursor.fetchone()
    recID = recipeinfo['id']
    session['rec_id'] = recID
    # запрос получения данных о препаратах, назначенных пациенту по коду рецепта
    cursor.execute(""" SELECT drug.title as drug_name, drug.ingridient, drug.country,
                drug.manufacturer, drug.price as drug_price,
                crosstrecdrug.drug_id, crosstrecdrug.count
                FROM drug
                JOIN crosstrecdrug ON drug.id = crosstrecdrug.drug_id WHERE crosstrecdrug.rec_id=%s""", (recID,))
    recDrugs = cursor.fetchall()
    if int(recipeinfo['status_id']) == 1:
        if recipeinfo['visit'] == 1:
            check_bal = "select sum(price) AS sum_rec from recipe where pacient_id=%s and recipe.category_id=%s and id=%s"
        else:
            check_bal = "select sum(price) AS sum_rec from recipe where pacient_id=%s and recipe.category_id=%s and id<%s"
    if int(recipeinfo['status_id'] == 2):
        check_bal = "select sum(price) AS sum_rec from recipe where pacient_id=%s and recipe.category_id=%s and id <=%s"
    get_fst_bal = "select balance from recipe where pacient_id=%s and category_id=%s and visit=1"
    cursor.execute(get_fst_bal, (recipeinfo['pacient_id'], recipeinfo['rec_cat_id']))
    default_balance = cursor.fetchall()
    cursor.execute(check_bal, (recipeinfo['pacient_id'], recipeinfo['rec_cat_id'], recID,))
    pat_bal = cursor.fetchall()
    diff = int(default_balance[0]['balance']) - int(pat_bal[0]['sum_rec'])
    update_balance = diff

    if request.method == 'POST':
        pharm_id = session['id']
        pharm_city = session['city_id']
        endDate = datetime.datetime.today()
        pharm_sum = int(request.form['price'])
        status = 2
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # если рецепт не отпущен фармацевтом,
        # то вносим изменения в базу  по айди выбранныго рецепта
        cursor.execute("""UPDATE recipe SET pharm_id=%s, endDate=%s, status_id=%s,
            price=%s, pharm_city=%s WHERE id=%s""",
            (pharm_id, endDate, status, pharm_sum, pharm_city, recID,))
        cursor.execute('insert into logs(user_id, time, ip_address, pacient_id, recipe_id, action) values(%s, %s, %s, %s, %s, "Отпустил рецепт")',
                        (session['id'], datetime.datetime.today(), '127.0.0.1', recipeinfo['pacient_id'], recID,))
        mysql.connection.commit()
        flash('Рецепт отпущен. Код рецепта: ' + str(recID), 'success')
        return redirect(url_for('recipe_info', recID=recID))
    return render_template('releaserecipe.html', recipes=recipes, recipeinfo=recipeinfo, pharminfo=pharminfo, recDrugs=recDrugs,
        new_balance=update_balance, userroleid=session['user_role_id'], userfio=session['user_fio'])


@app.route('/<int:pat_id>/add-data', methods=['GET', 'POST'])
def add_identific_data(pat_id):
    """ Функция добавления идентификационных данных пациента """
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
                        (session['id'], datetime.datetime.today(), '127.0.0.1', pat_id,))
        mysql.connection.commit()
        flash('Идентификационные данные успешно добавлены.', 'success')
        return redirect(url_for('recipe_info', recID=session['rec_id']))
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
    if 'loggedin' in session:
        user_id = session['user_role_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if user_id == 3: # Оператор_P
            # идентификатор Врача
            num1 = 1
            num2 = 3
        if user_id == 4: # Оператор_U
            # идентификатор Доктора
            num1 = 7
            num2 = 4
        cursor.execute(""" SELECT limits.id,
                            limits.indicator_limit, limits.indicator_used, limits.indicator_sum,
                            user.sName, user.fName, user.patr, user.phone_number as phone,
                            recipe_category.title as rec_category,
                            user_post.title as user_post
                            FROM limits
                            JOIN user on limits.doctor_id=user.id
                            JOIN recipe_category on limits.category_id=recipe_category.id
                            JOIN user_post on user.post_id=user_post.id
                            WHERE user.role_id=%s OR user.role_id=%s ORDER BY user.sName ASC """, (num1, num2,))
        limits = cursor.fetchall()
    else:
        return redirect(url_for('login'))
    return render_template('limits.html', limits=limits, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


@app.route('/limits/<int:limitID>/edit', methods = ['GET', 'POST'])
def edit_limit(limitID):
    """ Функция для изменения лимита в категории для выбранного пользователя """
    limituser =  get_user_limits(limitID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" select limits.id, limits.indicator_limit, limits.indicator_used,
                        limits.indicator_sum,
                        user.sName, user.fName, user.patr, user.phone_number as phone,
                        recipe_category.title as rec_category,
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
        user_id = session['user_role_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if user_id == 3:    # Оператор_P
            # вывести все препараты для врачей из базы
            cursor.execute(""" SELECT drug.id, drug.ingridient, drug.title as drug_title, drug.country,
                drug.manufacturer, drug_category.id as drCatid,
                drug_category.title as Drug_category,
                drug.price, drug.status_id
                FROM drug JOIN drug_category
                ON drug.category_id=drug_category.id
                WHERE drug.flagDrug=0
                order by drug.id""")
        if user_id == 4:    # Оператор_U
            # вывести все препараты для докторов из базы
            cursor.execute(""" SELECT drug.id, drug.ingridient, drug.title as drug_title, drug.country,
                drug.manufacturer, drug_category.id as drCatid,
                drug_category.title as Drug_category,
                drug.price, drug.status_id
                FROM drug JOIN drug_category
                ON drug.category_id=drug_category.id
                order by drug.id""")
        mysql.connection.commit()
        # передать полученный словарь словарей
        # в переменную и вернуть на страницу
        drugs=cursor.fetchall()
        return render_template('patient_drugs.html', drugs=drugs, userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id']) #вернуть полученные данные в шаблон страницы препаратов


@app.route('/add-drug')
def select2():
    """Возвращает данные для выпадающих списков на форме patient_add_drug.html """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    user_id = session['user_role_id']
    if user_id == 3:
        cursor.execute(""" SELECT id, title as drug_cat
                            from drug_category
                            where drug_category.title not like '%набор%' and flagCat=0
                            ORDER BY title """)
    if user_id == 4:
       cursor.execute(""" SELECT id, title as drug_cat
                            from drug_category
                            where drug_category.title not like '%набор%' and flagCat=1
                            ORDER BY title """)
    drugCat = cursor.fetchall()
    return render_template('patient_add_drug.html', drugCat=drugCat)


@app.route('/add-drug', methods=['GET', 'POST'])
def add_drug():
    """ Добавить новый препарат в базу """
    reg = request.form
    if request.method == "POST":
        ingridient = reg.get('ingridient')
        drug_title = reg.get('drug_title')
        country = reg.get('drug_country')
        manufacturer = reg.get('manufacturer')
        drugCat = reg.get('drugCat')
        price = reg.get('price')
        status = reg.get('drug_status')
        user_id = session['user_role_id']
        if user_id == 3:    # Оператор_P
            # индекс препарата для Врачей
            flagDrug = 0
        if user_id == 4:    # Оператор_P
            # индекс препарата для Докторов
            flagDrug = 1
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" INSERT INTO drug(ingridient, title, country,
                                manufacturer, category_id, flagDrug, price, status_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) """, (ingridient, drug_title,
                            country, manufacturer, drugCat, flagDrug, price, status))
        cursor.execute('SELECT last_insert_id() as newdrug')
        drug = cursor.fetchone()
        cursor.execute('insert into logs(user_id, time, ip_address, drug_id, action) values(%s, %s, %s, %s, "Добавил препарат")',
                        (session['id'], datetime.datetime.today(), '127.0.0.1', drug['newdrug']))
        mysql.connection.commit()
        flash('Препарат добавлен.', 'success')
        return redirect(url_for('drugs'))
    else:
        flash('ошибка', 'danger')
    return render_template('patient_add_drug.html', userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


@app.route('/drugs/<int:drugID>/edit', methods=['GET', 'POST'])
def edit_drug(drugID):
    """ Выполняет апдейт данных выбранного пользователем препарата """
    druginfo = get_drug_ID(drugID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        ingridient = request.form.get('ingridient')
        drug_title = request.form.get('drug_title')
        country = request.form.get('drug_country')
        manufacturer = request.form.get('manufacturer')
        price = request.form.get('price')
        status = request.form.get('drug_status')
        cursor.execute(""" UPDATE drug SET ingridient=%s, title=%s, country=%s,
                            manufacturer=%s, price=%s, status_id=%s  where id=%s""", (ingridient, drug_title,
                                country, manufacturer, price, status, drugID))
        cursor.execute('insert into logs(user_id, time, ip_address, drug_id, action) values(%s, %s, %s, %s, "Изменил данные о препарате")',
                        (session['id'], datetime.datetime.today(), '127.0.0.1', drugID,))
        mysql.connection.commit()
        flash('Информация о препарате успешно изменена', 'success')
        return redirect(url_for('drugs'))
    return render_template('patient_drug_edit.html', druginfo=druginfo, userrole=session['user_post'], userfio=session['user_fio'], userroleid=session['user_role_id'])


@app.route('/drugs/<int:drugID>/delete', methods=['GET', 'POST'])
def delete_drug(drugID):
    """ Удаляет выбранный пользователем препарат """
    druginfo = get_drug_ID(drugID)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('DELETE FROM drug WHERE id=%s', (drugID,))
        cursor.execute('insert into logs(user_id, time, ip_address, drug_id, action) values(%s, %s, %s, %s, "Удалил препарат")',
                        (session['id'], datetime.datetime.today(), '127.0.0.1', drugID,))
        mysql.connection.commit()
        flash('Препарат удален.', 'success')
        return redirect(url_for('drugs'))
    return render_template('delete_drug.html', druginfo=druginfo,)


# страница с информацией о выданных рецептах фармацевтами по городам
@app.route('/rel-recipes', methods=['GET','POST'])
def rel_recipes():
    """ Возвращает данные о всех выданных рецептах """
    if session['user_role_id'] in [3,9]: # Оператор_P, д1
        # индекс пациента Врача
        flag = 0
    if session['user_role_id'] in [4,8]:# Оператор_U, д2
        # индекс пациента Доктора
        flag = 1
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(""" SELECT recipe.id, recipe.pacient_id,
                        recipe.endDate, recipe.price,
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
                        JOIN city ON recipe.pharm_city=city.id
                        WHERE pacient.flagReg=%s and recipe.status_id=2
                        ORDER by recipe.endDate ASC """, (flag,))
    mysql.connection.commit()
    relRecipes = cursor.fetchall()
    return render_template('release_recipes.html', relRecipes=relRecipes, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


# страница с информацией о выписанных рецептах врачами
@app.route('/written-recipes', methods=['GET','POST'])
def written_recipes():
    """ Возвращает данные о всех выписанных рецептах """
    if session['user_role_id'] in [3,9]: # Оператор_P, д1
        # идентификатор  для пациента Врача
        num = 0
    if session['user_role_id'] in [4,8]:# Оператор_U, д2
        # идентификатор для пациента Доктора
        num = 1
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
                        JOIN city ON recipe.city_id=city.id
                        WHERE recipe.price > 0 and pacient.flagReg=%s
                        order by recipe.createDate ASC """, (num,))
    mysql.connection.commit()
    wrtRecipes = cursor.fetchall()
    return render_template('written_recipes.html', wrtRecipes=wrtRecipes, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


@app.route('/get-report')
def get_data_for_report_form():
    """ Возвращает данные для выпадающих списков на форме составления отчета form_for_report.html """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if 'loggedin' in session:
        if session['user_role_id'] in [3,9]:
            num = 0
        if session['user_role_id'] in [4, 8]:
            num = 1
        cursor.execute("""SELECT id, title as recCat
            FROM recipe_category WHERE flagCat=%s""", (num,))
        rec_cat = cursor.fetchall()
        cursor.execute('SELECT id, title as gender FROM gender')
        gender = cursor.fetchall()
        if session['user_role_id'] in [3, 9]:
            cursor.execute("""SELECT id, title as diagnos
                FROM diagnos WHERE flagDiag=%s ORDER BY title ASC""", (num,))

        if session['user_role_id'] in [4, 8]:
            cursor.execute("""SELECT id, title as diagnos
                FROM diagnos ORDER BY title ASC""")
        diagnos = cursor.fetchall()
        cursor.execute('SELECT id, title as city FROM city ORDER BY title ASC')
        cities = cursor.fetchall()
        cursor.execute('SELECT id, title as status from recipe_status')
        rec_status = cursor.fetchall()
    return render_template('form_for_reports.html', rec_cat=rec_cat, diagnos=diagnos, gender=gender, cities=cities, drugs=drugs, rec_status=rec_status, userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])


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
        cities = int(reg.get('cities'))
        rec_status = int(reg.get('rec_status'))
        visit = int(reg.get('visit'))
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if session['user_role_id'] in [3, 9]: # Оператор_P, д1
            # идентификатор для категории, диагноза д1
            num = 0
            if gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and rec_status == 0 and visit == 0:
                cursor.execute(""" SELECT * FROM report_data
                WHERE (createDate >= %s and createDate <=%s)
                    and (age between %s and %s)
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, num, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and flagCat=%s and flagDiag=%s""", (date1, date2, age1, age2, num, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s)
                    and status_id=2
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, num, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and city_id=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, cities, num, num,))

            elif gender != 0 and cities == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and gender_id=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, gender, num, num,))

            elif gender != 0 and cities == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and status_id=2
                    and gender_id=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, gender, num, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and status_id=2
                    and city_id=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, cities, num, num,))

            elif gender == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and category_id=%s
                    and status_id=1
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, rec_cat, num, num,))

            elif gender == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and category_id=%s
                    and status_id=2
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, rec_cat, num, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and visit=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, visit, num, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and status_id=2
                    and visit=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, visit, num, num,))

            elif gender == 0 and rec_cat == 0 and cities == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                WHERE (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and diag_id=%s and status_id=1
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, diagnos, num, num,))

            elif gender == 0 and rec_cat == 0 and cities == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and diag_id=%s and status_id=2
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, diagnos, num, num,))

            elif gender != 0 and rec_cat != 0 and diagnos != 0 and cities != 0 and visit != 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                    where (createDate >= %s and createDate <=%s) and
                        price > 0 and gender_id=%s
                        and category_id=%s
                        and city_id=%s and status_id=1
                        and visit=%s and (age between %s and %s)
                        and diag_id=%s
                        and flagCat=%s and flagDiag=%s """, (date1, date2, gender, rec_cat,
                                                 cities, visit, age1, age2, diagnos, num, num,))
            else:
                cursor.execute(""" SELECT * FROM report_data
                    where (endDate >= %s and endDate <=%s) and
                        price > 0 and gender_id=%s
                        and category_id=%s
                        and city_id=%s and status_id=2
                        and visit=%s and (age between %s and %s)
                        and diag_id=%s
                        and flagCat=%s and flagDiag=%s """, (date1, date2, gender, rec_cat,
                                                 cities, visit, age1, age2, diagnos, num, num,))

        if session['user_role_id'] in [4, 8]: # Оператор_U, д2
            # идентификатор для категории, диагноза д2
            num = 1
            if gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and rec_status == 0 and visit == 0:
                cursor.execute(""" SELECT * FROM report_data
                    WHERE (createDate >= %s and createDate <=%s)
                        and (age between %s and %s)
                        and flagCat=%s """, (date1, date2, age1, age2, num,))
            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and flagCat=%s """, (date1, date2, age1, age2, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s)
                    and status_id=2
                    and flagCat=%s """, (date1, date2, age1, age2, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and city_id=%s
                    and flagCat=%s""", (date1, date2, age1, age2, cities, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and status_id=2
                    and city_id=%s
                    and flagCat=%s""", (date1, date2, age1, age2, cities, num,))

            elif gender != 0 and cities == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and gender_id=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, gender, num, num,))

            elif gender != 0 and cities == 0 and rec_cat == 0 and diagnos == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and gender_id=%s
                    and flagCat=%s and flagDiag=%s """, (date1, date2, age1, age2, gender, num, num,))

            elif gender == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and category_id=%s
                    and status_id=1
                    and flagCat=%s""", (date1, date2, age1, age2, rec_cat, num,))

            elif gender == 0 and diagnos == 0 and cities == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and category_id=%s
                    and status_id=2
                    and flagCat=%s """, (date1, date2, age1, age2, rec_cat, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                where (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and status_id=1
                    and visit=%s
                    and flagCat=%s """, (date1, date2, age1, age2, visit, num,))

            elif gender == 0 and rec_cat == 0 and diagnos == 0 and cities == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and status_id=2
                    and visit=%s
                    and flagCat=%s""", (date1, date2, age1, age2, visit, num,))

            elif gender == 0 and rec_cat == 0 and cities == 0 and visit == 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                WHERE (createDate >= %s and createDate <=%s)
                    and (age between %s and %s) and diag_id=%s and status_id=1
                    and flagCat=%s""", (date1, date2, age1, age2, diagnos, num,))

            elif gender == 0 and rec_cat == 0 and cities == 0 and visit == 0 and rec_status == 2:
                cursor.execute(""" SELECT * FROM report_data
                where (endDate >= %s and endDate <=%s)
                    and (age between %s and %s) and diag_id=%s and status_id=2
                    and flagCat=%s """, (date1, date2, age1, age2, diagnos, num,))

            elif gender != 0 and rec_cat != 0 and diagnos != 0 and cities != 0 and visit != 0 and rec_status == 1:
                cursor.execute(""" SELECT * FROM report_data
                    where (createDate >= %s and createDate <=%s) and
                        price > 0 and gender_id=%s
                        and category_id=%s
                        and city_id=%s and status_id=1
                        and visit=%s and (age between %s and %s)
                        and diag_id=%s
                        and flagCat=%s """, (date1, date2, gender, rec_cat,
                                                 cities, visit, age1, age2, diagnos, num,))
            else:
                cursor.execute(""" SELECT * FROM report_data
                    where (endDate >= %s and endDate <=%s) and
                        price > 0 and gender_id=%s
                        and category_id=%s
                        and city_id=%s and status_id=2
                        and visit=%s and (age between %s and %s)
                        and diag_id=%s
                        and flagCat=%s """, (date1, date2, gender, rec_cat,
                                                 cities, visit, age1, age2, diagnos, num,))
        mysql.connection.commit()
        records = cursor.fetchall()

        cursor.execute(""" SELECT drug_name, city_name, category, SUM(COUNT) AS total,
                CASE drug_id
                    WHEN 80 THEN 'Набор: Нормальные роды'
                    WHEN 315 THEN 'Набор: Кесарево сечение'
                    WHEN 285 THEN 'Набор: Взрослый хирургический'
                    WHEN 359 THEN 'Набор: Малый хирургический'
                    WHEN 250 THEN 'Набор: детский хирургический'
                END AS Nabor
                FROM drugs_for_report
                WHERE (endDate >=%s and endDate <=%s) and flagCat=%s
                GROUP BY drug_name, city_name, category """, (date1, date2, num,))
        releasing_drugs = cursor.fetchall()
        return render_template('report.html', records=records, userrole=session['user_post'], rec_status=rec_status,
           releasing_drugs=releasing_drugs, userroleid=session['user_role_id'], userfio=session['user_fio'])
    return render_template('form_for_reports.html',userrole=session['user_post'],
            userroleid=session['user_role_id'], userfio=session['user_fio'])



if __name__ == '__main__':
    app.run(debug=True)

