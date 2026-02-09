from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, flash
from flask import Flask, render_template, request, redirect, url_for
from flask_login import login_required, current_user, LoginManager, UserMixin, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash # 🔑 أضف check_password_hash
from sqlalchemy import UniqueConstraint, cast, Date, Integer # 👈 هنا
from flask import Flask, request, jsonify # 👈 تأكد من وجود jsonify
from sqlalchemy.exc import OperationalError
from datetime import datetime, time as datetime_time # 👈 تم إضافة time
from flask import request, redirect, url_for, render_template, flash, current_app
# ...
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from flask import render_template
from sqlalchemy.exc import OperationalError
from flask import jsonify
from flask import send_file # تأكد من أن send_file مستوردة في بداية الملف
from io import BytesIO
import pandas as pd
from sqlalchemy import func
from sqlalchemy import UniqueConstraint, cast, Date
from flask import request, redirect, url_for, render_template # تأكد من استيراد هذه الدوال
# تأكد أيضاً من استيراد MonthlyGrade, Student, db, get_current_year
from flask_migrate import Migrate
import pytz
# 🆕 إضافة مكتبة التشفير
from werkzeug.security import generate_password_hash
from functools import wraps 
# 🔑 الاستيرادات اللازمة لـ Flask-Admin
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from wtforms import validators, fields
from wtforms.widgets import PasswordInput

# 🆕 إضافات لتصدير Excel
from io import BytesIO
import pandas as pd
import datetime 
# =========================================================
# 1. إعداد الاتصال والتطبيق
# =========================================================
# 🛑🛑🛑 يجب التأكد من صحة هذا المسار وبيانات الاعتماد 🛑🛑🛑
# app.py - حوالي السطر 45
# المسار الجديد، تأكد من أن هذا السطر يبدأ بـ ' و ينتهي بـ ' فقط، بدون فراغات!
POSTGRES_URI =  'postgresql://neondb_owner:npg_h2AtzWpaV0MX@ep-dry-sky-a4ah9a5s-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
app = Flask(__name__)
CORS(app)
TIMEZONE = 'Asia/Riyadh' 


# قم بإنشاء URI بالبنية المعتادة لتجنب أي مشاكل

# 1. تعيين الإعدادات الضرورية أولاً
app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRES_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # موصى به
app.config['SECRET_KEY'] = 'your_strong_secret_key_here'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0



# 2. إنشاء كائن قاعدة البيانات (db)
db = SQLAlchemy(app)

# 3. تهيئة Flask-Migrate (بعد إنشاء db)
migrate = Migrate(app, db)


# =========================================================
# 2. دالة لإنشاء الجداول (للاستخدام اليدوي)
# =========================================================
def create_db_tables():
    """ينشئ جميع الجداول المعرفة في الموديلات."""
    with app.app_context():
        db.create_all()
        print("تم إنشاء الجداول بنجاح.")


# =========================================================
# 3. الموديلات (SQLAlchemy Models) - أمثلة افتراضية
# =========================================================
def allowed_file(filename):
    """التحقق من أن الملف المرفوع هو Excel أو CSV."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}


@app.route('/test_db_connection')
def test_db_connection():
    try:
        # محاولة تنفيذ استعلام بسيط جداً للتأكد من الاتصال
        # هذا سيجبر SQLAlchemy على محاولة الاتصال بالخادم
        db.session.execute(db.text('SELECT 1')) 
        # إذا نجح الاستعلام
        return jsonify({
            "status": "Success",
            "message_ar": "تم الاتصال بقاعدة البيانات بنجاح!",
            "uri": app.config['SQLALCHEMY_DATABASE_URI']
        }), 200
    except OperationalError as e:
        # إذا فشل الاتصال (خطأ OperationalError)
        return jsonify({
            "status": "Error",
            "message_ar": "فشل الاتصال بقاعدة البيانات.",
            "error_detail": str(e),
            "uri": app.config['SQLALCHEMY_DATABASE_URI']
        }), 500
    except Exception as e:
        # أي خطأ آخر (مثل خطأ في الاسم/المضيف)
        return jsonify({
            "status": "Error",
            "message_ar": "حدث خطأ غير متوقع أثناء محاولة الاتصال.",
            "error_detail": str(e),
            "uri": app.config['SQLALCHEMY_DATABASE_URI']
        }), 500
@app.route('/available_months/<string:zk_id>', methods=['GET']) 
def available_months(zk_id):
    try:
        student = Student.query.filter_by(zk_user_id=zk_id).first()
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        result = []
        
        # 1. جلب الأشهر الشهرية (استعلام monthly_data الذي كان مفقوداً أو معلّقاً)
        monthly_data = db.session.query(
            MonthlyGrade.month_name,
            MonthlyGrade.year 
        ).filter(
            MonthlyGrade.student_zk_id == zk_id
        ).distinct().all() 
        
        # 2. جلب السنوات النصفية (كـ MidTerm)
        mid_term_data = db.session.query(
            MidTermGrade.academic_year.label('year')
        ).filter(
            MidTermGrade.student_zk_id == zk_id
        ).distinct().all()

        # 3. تجميع النتائج
        
        # 🛑 هذه هي الحلقة التي كانت تشتكي من أن monthly_data غير معرّف
        for item in monthly_data: 
            result.append({
                'month_name': item.month_name,
                'year': item.year,
                'type': 'monthly' 
            })
            
        # إضافة التقارير النصفية (مع التعريب)
        
            
        result.sort(key=lambda x: x['year'], reverse=True) 
        
        return jsonify(result), 200

    except Exception as e:
        print(f"FATAL ERROR in available_months: {e}")
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    
# ... (بقية المسارات: attendance, grades_report, etc.) ...

# app.py (النسخة النهائية والمصححة بالكامل لدالة grades_report)
 # تأكد من استيراد func
from sqlalchemy import func, cast, Integer, String
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, cast, Date, Integer, String, func # إضافة String و Integer هنا

# ... (يفترض وجود باقي الاستيرادات والمكتبات هنا) ...

# 🛑🛑🛑 إضافة ثابت MONTHS_MAP هنا 🛑🛑🛑
MONTHS_MAP = [
    'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
    'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
]
# 🛑🛑🛑 نهاية تعريف ثابت MONTHS_MAP 🛑🛑🛑

#//هنا الداله عرض الدرجات الشهريه والنصفيه والنهائيه في التطبيق 
@app.route('/grades_report/<zk_id>', methods=['POST'])
def grades_report(zk_id):
    # 1. التهيئة الأولية لضمان وجود المتغيرات في جميع مسارات الكود
    grades = []
    grades_list = []
    grades_query = None  # تهيئة grades_query لاستخدامه في التقرير الشهري
    
    # تعيين قيم افتراضية لـ final_total_aggregate
    final_total_aggregate = 0
    
    # تعيين قيم افتراضية لـ ranking_db و result_db
    ranking_db = 'غير محدد'
    result_db = 'غير محدد'

    try:
        data = request.get_json()
        month_name = data.get('month_name')
        year = data.get('year')
        
        if not month_name or not year:
            return jsonify({'message': 'Missing month_name or year in request body'}), 400

        student = Student.query.filter_by(zk_user_id=zk_id).first()
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        class_name = 'غير محدد'
        if hasattr(student, 'class_id') and student.class_id:
            student_class = Class.query.get(student.class_id)
            if student_class:
                class_name = student_class.name

        # 🔑 الاعتماد على النموذج MonthlyGrade (أو Grade)
        MonthlyGradeModel = globals().get('MonthlyGrade')
        if not MonthlyGradeModel:
            MonthlyGradeModel = globals().get('Grade')
            if not MonthlyGradeModel:
                return jsonify({'message': 'Grade Model not defined in your application'}), 500

        
        # ----------------------------------------------------
        # 2. تحديد نوع التقرير والاستعلام عن البيانات
        # ----------------------------------------------------
        if month_name == 'التقرير النصفي' or month_name.lower() == 'midterm':
            try:
                # الاستعلام عن التقرير النصفي (MidTermGrade)
                grades = db.session.query(MidTermGrade).filter(
                    MidTermGrade.student_zk_id == str(zk_id),
                    MidTermGrade.academic_year == int(year)
                ).all()
                
            except Exception as e:
                print(f"FATAL MidTermGrade QUERY ERROR: {e}")
                return jsonify({'message': f'MidTermGrade query failed: {str(e)}'}), 500
            
            
        
        
        elif month_name in MONTHS_MAP: # 👈 الآن MONTHS_MAP معرّف
            # تقرير شهري
            grades_query = MonthlyGradeModel.query.with_entities(
                MonthlyGradeModel.subject_name,
                func.coalesce(MonthlyGradeModel.homework_grade, 0).label('homework_grade'),
                func.coalesce(MonthlyGradeModel.oral_grade, 0).label('oral_grade'),
                func.coalesce(MonthlyGradeModel.attendance_grade, 0).label('attendance_grade'),
                func.coalesce(MonthlyGradeModel.written_grade, 0).label('written_grade'),
                func.coalesce(MonthlyGradeModel.app, 0).label('app'),
                
                func.cast(func.coalesce(MonthlyGradeModel.final_total_grade, 0), Integer).label('final_total_grade'),
                func.coalesce(MonthlyGradeModel.supplies, 0).label('supplies'),
                
                # ✅ جلب حقل النتيجة
                func.coalesce(MonthlyGradeModel.result, 'غير محدد').label('result'),
                # إضافة حقل ranking للتقارير الشهرية لضمان عدم وجود خطأ في الكود السفلي
                func.cast('غير محدد', String).label('ranking')
            ).filter(
                MonthlyGradeModel.student_zk_id == zk_id,
                MonthlyGradeModel.month_name == month_name, 
                MonthlyGradeModel.year == int(year) 
            )
            
            # 🛑 هنا يجب ملء المتغير 'grades' من الاستعلام الشهري
            grades = grades_query.all()

        else:
            # إذا كان month_name غير معروف
            return jsonify({'message': f'Invalid report month key: {month_name}'}), 400


        # ----------------------------------------------------
        # 3. معالجة البيانات وبناء الرد (تستخدم grades و grades_list)
        # ----------------------------------------------------

        # التحقق من عدم وجود بيانات في كلا المسارين (الشهري والنصفي)
        if not grades:
            return jsonify({'message': f'No report found for student {zk_id} using key: {month_name}/{year}'}), 404

        # 🔑 تحديث قيم ranking_db و result_db من أول سجل تم العثور عليه
        # هذا يجب أن يتم فقط بعد التأكد من أن grades ليست فارغة
        if month_name == 'التقرير النصفي' or month_name.lower() == 'midterm':
            # يجب استخدام حقول MidTermGrade الخاصة بالترتيب والنتيجة
            final_total = int(grades[0].final_term_grade or 0) if hasattr(grades[0], 'final_term_grade') else 0
            
            # 2. النتيجة النهائية (result_db) <- mid_term_result
            result_db = grades[0].mid_term_result if hasattr(grades[0], 'mid_term_result') and grades[0].mid_term_result is not None else 'غير محدد'
            
            # 3. الترتيب (ranking_db) <- mid_term_ranking
            ranking_db = grades[0].mid_term_ranking if hasattr(grades[0], 'mid_term_ranking') and grades[0].mid_term_ranking is not None else 'غير محدد'

            
            
        else: # التقرير الشهري
            # استخدام حقول MonthlyGrade العامة
            ranking_db = grades[0].ranking if hasattr(grades[0], 'ranking') and grades[0].ranking is not None else 'غير محدد'
            result_db = grades[0].result if hasattr(grades[0], 'result') and grades[0].result is not None else 'غير محدد'


        # حلقة التكرار لملء grades_list
        for grade in grades:
            
            # 🛑 منطق الدرجات النصفية 
            if month_name == 'التقرير النصفي' or month_name.lower() == 'midterm':
                
                # استخدام hasattr للتحقق من وجود الحقول الخاصة بالتقرير النصفي
                accumulated_grade = int(grade.accumulated_grade or 0) if hasattr(grade, 'accumulated_grade') else 0
                end_term_grade = int(grade.end_term_grade or 0) if hasattr(grade, 'end_term_grade') else 0
                term_total_grade = int(grade.term_total_grade or 0) if hasattr(grade, 'term_total_grade') else 0
                
                # لحساب المجموع الإجمالي للتقرير النصفي، يجب استخدام term_total_grade
                

                grades_list.append({
                    'id': grade.id,
                    'subject_name': grade.subject_name,
                    'accumulated_grade': accumulated_grade,
                    'end_term_grade': end_term_grade,
                    'term_total_grade': term_total_grade,
                    'result': grade.result if hasattr(grade, 'result') else 'غير محدد',
                    'mid_term_ranking': grade.mid_term_ranking if hasattr(grade, 'mid_term_ranking') else 'غير محدد'
                })
            
            # 🛑 منطق الدرجات الشهرية
            elif month_name in MONTHS_MAP:
                
                # حساب final_grade_value للتقرير الشهري
                raw_grade_str = str(grade.final_total_grade).strip()
                try:
                    final_grade_value = int(raw_grade_str)
                except (TypeError, ValueError):
                    final_grade_value = 0
                    
                final_total_aggregate += final_grade_value
                
                grades_list.append({
                    'subject_name': grade.subject_name,
                    'homework_grade': int(grade.homework_grade or 0),
                    'oral_grade': int(grade.oral_grade or 0),
                    'attendance_grade': int(grade.attendance_grade or 0),
                    'written_grade': int(grade.written_grade or 0),
                    'app': int(grade.app or 0),
                    'final_total_grade': final_grade_value,
                    'supplies': int(grade.supplies or 0),
                    'result': grade.result if grade.result else 'غير محدد',
                })
                
        # 4. بناء ملخص التقرير النهائي
        report_data = {
            'student_name': student.name,
            'class_name': class_name,
            'month_name': month_name,
            'year': int(year),
            'final_total': int(final_total),
            
            'final_result': result_db, 
            'ranking': ranking_db, 
            'grades': grades_list,
        }

        return jsonify(report_data), 200

    except Exception as e:
        # 5. معالجة الأخطاء العامة
        print(f"FATAL ERROR during grades report generation: {e}") 
        return jsonify({'message': f'Internal Server Error: {str(e)}'}), 500
    
@app.route('/change_password', methods=['POST'])
def change_password():
    
    try:
        data = request.get_json()
        username = data.get('username') # 🔑 نحتاج لاسم المستخدم من الطلب
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        # 1. التحقق من البيانات الأساسية
        if not username or not old_password or not new_password:
            return jsonify({"message": "❌ يجب إدخال جميع الحقول: اسم المستخدم وكلمتي المرور."}), 400

        # 2. البحث عن المستخدم (الاعتماد على اسم المستخدم المرسل)
        user = User.query.filter_by(username=username).first()

        if not user:
             return jsonify({"message": "❌ المستخدم غير موجود."}), 404
        
        # 3. التحقق من كلمة المرور القديمة (باستخدام التشفير)
        if user.password== old_password:
            return jsonify({"message": "❌ كلمة المرور القديمة غير صحيحة."}), 401
            
        # 4. التحقق من دور المستخدم (للسماح لأولياء الأمور فقط)
        if user.role != 'parent':
            return jsonify({"message": "❌ ليس لديك صلاحية تغيير كلمة المرور."}), 403

        # 5. تشفير وحفظ كلمة المرور الجديدة
        user.password = new_password
        db.session.commit()
        
        # 6. النجاح
        return jsonify({"message": "✅ تم تغيير كلمة المرور بنجاح."}), 200

    except Exception as e:
        print(f"Error changing password: {e}") 
        db.session.rollback()
        return jsonify({"message": "❌ حدث خطأ داخلي أثناء تغيير كلمة المرور."}), 500
    
    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++=
# 🆕 مسار استرداد الدرجات (MidTerm, Monthly, Final)
# ------------------------------------------
# المسار يتطابق مع /api/grades/<student_id>/<GradeType>/<year>

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    
# مسار الدرجات النصفية (MidTerm)
@app.route('/api/grades/<int:student_id>/midterm/<int:year>', methods=['GET'])
def get_mid_term_grades(student_id, year):

# مسار الدرجات الشهرية (Monthly) - أضف هذا المسار أيضاً
 @app.route('/api/grades/<int:student_id>/Monthly/<int:year>', methods=['GET'])
 def get_monthly_grades(student_id, year):
    # نستخدم نفس منطق MidTerm لكن مع MonthlyGrade
    GradeModel = MonthlyGrade
    grade_type = 'Monthly'
    # ... (بقية منطق الدالة تماماً كدالة get_mid_term_grades لكن باستخدام MonthlyGrade)
    # لتجنب التكرار، يمكنك نسخ جسم دالة MidTerm وتغيير اسم GradeModel فقط:
    # GradeModel = MonthlyGrade
    
    # ... (كمل الكود هنا) ...
    # مثال للتكملة:
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"message": "❌ الطالب غير موجود."}), 404
        
    try:
        grades = db.session.query(
            GradeModel.grade_value,
            Subject.name.label('subject_name'),
            Subject.max_grade
        ).join(Subject).filter(
            GradeModel.student_id == student_id,
            GradeModel.year == year
        ).all()
        
        grades_data = []
        for grade in grades:
            grades_data.append({
                'subject_name': grade.subject_name,
                'grade_value': grade.grade_value,
                'max_grade': grade.max_grade
            })
            
        return jsonify(grades_data), 200

    except Exception as e:
        print(f"Error fetching {grade_type} grades: {e}") 
        return jsonify({"message": f"❌ خطأ داخلي في {grade_type} grades. التفاصيل: {str(e)}"}), 500
    
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    
@app.route('/api/grades/available_months/<string:zk_id>', methods=['GET'])
def get_available_months(zk_id):
    try:
        student = Student.query.filter_by(zk_user_id=zk_id).first() 

        if not student:
            # ✅ إرجاع 404 إذا لم يتم العثور على الطالب
            return jsonify({'message': f'Student with zk_id {zk_id} not found'}), 404

        # 2. الاستعلام: جلب حقول month_name و year مباشرة
        available_months = db.session.query(
            MonthlyGrade.month_name,
            MonthlyGrade.year
        ).filter(
            MonthlyGrade.student_zk_id == zk_id
        ).group_by(
            MonthlyGrade.month_name,
            MonthlyGrade.year
        ).order_by(
            MonthlyGrade.year.desc(), 
            MonthlyGrade.month_name.desc()
        ).all()

        # 3. تهيئة البيانات للإرسال
        result = []
        for month_name, year in available_months: 
            result.append({
                'month_name': month_name,
                'year': year
            })

        # 4. إرجاع النتيجة النهائية (مع المسافة البادئة الصحيحة)
        return jsonify(result), 200 

    except Exception as e:
        # معالجة عامة للأخطاء
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

MONTH_ORDER = {
    'يناير': 1, 'فبراير': 2, 'مارس': 3, 'أبريل': 4,
    'مايو': 5, 'يونيو': 6, 'يوليو': 7, 'أغسطس': 8,
    'سبتمبر': 9, 'أكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12
}

# 🔑 دالة مساعدة لفرز نتائج الأشهر في بايثون (Sort Key)
def month_sort_key(item):
    month_name, year = item
    # الترتيب أولاً تنازلياً حسب السنة (-year)
    # ثم تنازلياً حسب رقم الشهر (-MONTH_ORDER)
    return (-year, -MONTH_ORDER.get(month_name, 0))
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

@app.route('/api/grades/<path:full_path>', methods=['GET'])
def debug_grades_catch_all(full_path):
    # إذا وصل الطلب إلى هنا، فلن ترى 404 بل سترى 200 أو 418
    # سيعرض هذا المسار المسار الكامل الذي استقبله Flask بعد /api/grades/
    
    # ⚠️ هذه رسالة اختبار فقط ⚠️
    return jsonify({
        "message": "✅ تم العثور على المسار بنجاح!",
        "received_path": full_path # يجب أن يكون 1002/MidTerm/2025
    }), 200
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    
@app.route('/api/parent/attendance/<int:zk_id>/<string:start_date>/<string:end_date>', methods=['GET'])
def get_student_attendance_report(zk_id, start_date, end_date):
    """
    مسار API لجلب سجل الحضور والغياب للطالب.
    يتم استدعاؤه من تطبيق ولي الأمر.
    مثال: /api/parent/attendance/123/2024-09-01/2024-09-30
    """
    try:
        # تحويل التواريخ من سلسلة نصية إلى كائنات Date
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        # جلب بيانات الطالب للتحقق ولعرضها في التقرير
        student = Student.query.filter_by(zk_user_id=zk_id).first()
        if not student:
            return jsonify({'message': '❌ خطأ: لم يتم العثور على الطالب بالرقم المحدد.'}), 404

        # جلب سجلات الحضور للطالب ضمن النطاق الزمني
        attendance_records = db.session.query(Attendance).\
            filter(
                Attendance.student_zk_id == zk_id,
                # استخدام cast(Date) لضمان المقارنة الصحيحة مع الحقل التاريخي في قاعدة البيانات
                cast(Attendance.date, Date) >= start_date_obj,
                cast(Attendance.date, Date) <= end_date_obj
            ).order_by(Attendance.date.asc()).all()
            
        # تجهيز البيانات للإرسال إلى التطبيق بصيغة JSON
        report_data = []
        absence_count = 0
        
        for record in attendance_records:
            # حالة الحضور/الغياب: 'Present', 'Absent', 'Late'
            status_arabic = {
                'Present': 'حاضر ✅',
                'Absent': 'غائب ❌',
                'Late': 'متأخر 🟡'
            }.get(record.status, 'غير محدد')
            
            if record.status == 'Absent':
                absence_count += 1
            
            report_data.append({
                'date': record.date.strftime('%Y-%m-%d'),
                'status': status_arabic
            })

        return jsonify({
            'status': 'success',
            'student_name': student.name,
            'class_name': student.current_class.name if student.current_class else 'غير محدد',
            'total_days': len(report_data),
            'absence_count': absence_count,
            'attendance_records': report_data
        })

    except ValueError:
        return jsonify({'message': '❌ خطأ في تنسيق التاريخ. يجب أن يكون YYYY-MM-DD.'}), 400
    except Exception as e:
        # لغرض التصحيح، يمكن أن تعرض رسالة الخطأ
        print(f"Error fetching attendance: {e}")
        return jsonify({'message': '❌ حدث خطأ داخلي أثناء جلب البيانات.'}), 500

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

@app.route('/admin/grades/import', methods=['GET', 'POST'])
@login_required
def import_monthly_grades():
    if request.method == 'POST':
        # التحقق من وجود ملف مرفوع
        if 'file' not in request.files:
            flash('لم يتم رفع أي ملف.', 'danger')
            return redirect(url_for('import_monthly_grades'))
        
        file = request.files['file']
        
        # التحقق من اختيار ملف
        if file.filename == '':
            flash('الرجاء اختيار ملف صالح.', 'danger')
            return redirect(url_for('import_monthly_grades'))

        # التحقق من نوع الملف
        if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
            try:
                # 🔑 تمرير الملف إلى دالة المعالجة
                success, message = process_monthly_grades_file(file)
                
                if success:
                    flash(f'تم استيراد الدرجات بنجاح: {message}', 'success')
                else:
                    flash(f'فشل الاستيراد: {message}', 'danger')
                
                return redirect(url_for('import_monthly_grades'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ غير متوقع أثناء معالجة الملف: {str(e)}', 'danger')
                return redirect(url_for('import_monthly_grades'))
        
        else:
            flash('صيغة الملف غير مدعومة. الرجاء استخدام ملف Excel (.xlsx) أو CSV.', 'danger')
            return redirect(url_for('import_monthly_grades'))

    return render_template('import_grades_page.html')


# أضف هذه الدالة الجديدة إلى app.py
def process_monthly_grades_file(file):
    
    # تحديد صيغة الملف
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # 1. تعريف الأعمدة المطلوبة والتأكد من وجودها
    required_cols = ['zk_user_id', 'academic_year', 'subject_name', 'month', 'grade_value']
    if not all(col in df.columns for col in required_cols):
        missing_cols = [col for col in required_cols if col not in df.columns]
        return False, f"الملف يفتقد لبعض الأعمدة المطلوبة: {', '.join(missing_cols)}"

    # 2. حلقة التكرار على صفوف البيانات
    rows_imported = 0
    errors = []
    
    for index, row in df.iterrows():
        try:
            zk_id = str(row['zk_user_id']).strip()
            year = int(row['academic_year'])
            subject_name = str(row['subject_name']).strip()
            month_name = str(row['month']).strip()
            grade_value = float(row['grade_value'])
            
            # التحقق من وجود الطالب
            student = Student.query.filter_by(zk_user_id=zk_id).first()
            if not student:
                errors.append(f"السطر {index+2}: الطالب ID {zk_id} غير موجود.")
                continue

            # التحقق من وجود المادة
            subject = Subject.query.filter_by(name=subject_name).first()
            if not subject:
                errors.append(f"السطر {index+2}: المادة {subject_name} غير موجودة.")
                continue

            # التحقق من الشهر وتعيين قيمة عددية له (لتجنب الأخطاء)
            month_mapping = {
                'سبتمبر': 9, 'اكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12,
                'يناير': 1, 'فبراير': 2, 'مارس': 3, 'ابريل': 4, 'مايو': 5, 'يونيو': 6
            }
            month_num = month_mapping.get(month_name.lower())
            
            if not month_num:
                errors.append(f"السطر {index+2}: الشهر '{month_name}' غير صالح.")
                continue

            # البحث عن سجل الدرجة، أو إنشاؤه
            grade_record = MonthlyGrade.query.filter_by(
                student_zk_id=zk_id,
                academic_year=year,
                subject_name=subject_name,
                month=month_num
            ).first()

            if grade_record:
                grade_record.grade_value = grade_value
            else:
                grade_record = MonthlyGrade(
                    student_zk_id=zk_id,
                    academic_year=year,
                    subject_name=subject_name,
                    month=month_num,
                    grade_value=grade_value
                )
                db.session.add(grade_record)
                
            rows_imported += 1
            
        except ValueError as e:
            errors.append(f"السطر {index+2}: خطأ في صيغة البيانات (العام، الدرجة، الشهر): {e}")
        except Exception as e:
            errors.append(f"السطر {index+2}: خطأ غير معروف: {e}")
            
    # 3. حفظ التغييرات في قاعدة البيانات
    if errors:
        db.session.rollback()
        return False, f"تم العثور على {len(errors)} خطأ. بعض الأمثلة: {', '.join(errors[:3])}"
    else:
        db.session.commit()
        return True, f"تم استيراد وتحديث {rows_imported} سجل درجة بنجاح."


# 4. تهيئة Flask-Login
login_manager = LoginManager() # 🛑 يجب تعريف المتغير هنا أولاً
login_manager.init_app(app)
# مسار صفحة تسجيل الدخول إذا لم يكن المستخدم مسجلاً
login_manager.login_view = 'login' 
login_manager.login_message = "الرجاء تسجيل الدخول للوصول لهذه الصفحة."
login_manager.login_message_category = "info"

# 🛑🛑 يجب أن يأتي الكود أعلاه قبل الكود أدناه 🛑🛑
# ----------------------------------------------------

# 5. دالة تحميل المستخدم (يجب أن تكون ثانياً)
@login_manager.user_loader # 🛑 الآن يمكن استخدام المتغير login_manager
def load_user(user_id):
    """تحميل المستخدم من الـ Session"""
    return db.session.get(User, int(user_id))
# تعيين المنطقة الزمنية لليمن
YEMEN_TZ = pytz.timezone('Asia/Aden')


def admin_required(f):
    """ديكور يضمن أن المستخدم الحالي هو مسؤول (admin)."""
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('غير مصرح لك بالوصول لهذه الصفحة. يرجى تسجيل الدخول كمسؤول.', 'danger')
            # 🛑 تم التعديل: إعادة التوجيه إلى 'login' بدلاً من 'index' لأسباب أمنية ولحل خطأ BuildError
            return redirect(url_for('login')) 
        return f(*args, **kwargs)
    return decorated_function


class User(db.Model, UserMixin): 
  __tablename__ = 'users'
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(80), unique=True, nullable=False)
  password = db.Column(db.String(256))
  role = db.Column(db.String(20), default='parent')
  students = db.relationship('Student', backref='parent', lazy=True)



class Class(db.Model):
# ... (باقي الموديلات كما هي)
# ...
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(
        db.Integer, 
        nullable=False, 
        default=datetime.datetime.now(YEMEN_TZ).year)

    next_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    next_class = db.relationship('Class', remote_side=[id], backref='previous_class', uselist=False)

    __table_args__ = (
        UniqueConstraint('name', 'academic_year', name='_class_year_uc'),
    )

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    zk_user_id = db.Column(db.String(20), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    current_class = db.relationship('Class', backref='students', lazy=True)

    monthly_grades = db.relationship('Grade', backref='student', lazy='dynamic')
    mid_term_grades = db.relationship('MidTermGrade', backref='student', lazy='dynamic')
    final_grades = db.relationship('FinalGrade', backref='student', lazy='dynamic')
#________________________________________________________________________________________________________________________________
class AttendanceView(ModelView):
    # 🛑 تحديث column_list ليعكس أسماء الأعمدة الجديدة
    column_list = ('columnid', 'student_zk_id', 'date', 'time', 'status', 'number_fin')
    column_labels = {
        'columnid': 'ID', # عرض الاسم الداخلي columnid كـ ID
        'student_zk_id': 'ZK ID', 
        'date': 'التاريخ', 
        'time': 'الوقت', 
        'status': 'الحالة',
        'number_fin': 'رقم FIN'
    }
# 🆕 نموذج الحضور والغياب المحدث
class Attendance(db.Model):
    __tablename__ = 'attendance' # افتراضي، يمكنك تغييره حسب ما هو موجود لديك فعلياً
    
    id = db.Column(db.Integer, primary_key=True) 
    
    # 🚀 التصحيح: المفتاح الأجنبي يشير الآن إلى 'students.zk_user_id' (اسم الجدول الصحيح)
    student_zk_id = db.Column(db.String(50), db.ForeignKey('students.zk_user_id'), nullable=False)
    
    date = db.Column(db.Date, nullable=False) 
    time = db.Column(db.Time, nullable=True) 
    status = db.Column(db.String(10), nullable=False) 
    number_fin = db.Column(db.Integer, nullable=True) 
    
    # علاقة للوصول إلى بيانات الطالب (إذا لم تكن موجودة بالفعل)
    student_info = db.relationship('Student', foreign_keys=[student_zk_id], primaryjoin="Student.zk_user_id == Attendance.student_zk_id")
    
    __table_args__ = (
        UniqueConstraint('student_zk_id', 'date', name='_student_date_uc'),
    )
@app.route('/admin/attendance/entry', methods=['GET', 'POST'])
@login_required
def admin_attendance_entry():
    """
    يعرض نموذج رفع ملف بيانات الحضور الخام (Excel/CSV) ويقوم بمعالجة الملف المرفوع.
    يتوقع الأعمدة: Student ZK ID, Date, Time (اختياري/يمكن أن يكون NULL), Number FIN.
    """
    if request.method == 'POST':
        # 1. التحقق من وجود ملف في الطلب
        if 'file' not in request.files:
            flash('لم يتم رفع أي ملف.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # 2. التحقق من اختيار ملف
        if file.filename == '':
            flash('لم يتم اختيار ملف.', 'danger')
            return redirect(request.url)
            
        # 3. معالجة الملف إذا كان صالحًا
        if file and allowed_file(file.filename):
            try:
                file_content = file.read()
                data = BytesIO(file_content)
                
                # قراءة الملف بناءً على الامتداد
                if file.filename.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(data)
                elif file.filename.endswith('.csv'):
                    df = pd.read_csv(data)
                else:
                    flash('صيغة الملف غير مدعومة. يرجى استخدام Excel (.xlsx, .xls) أو CSV.', 'danger')
                    return redirect(request.url)

                # 💡 تحسين عملية التحقق من الأعمدة
                REQUIRED_COLUMNS = ['Student ZK ID', 'Date', 'Number FIN']
                
                # 1. تطبيق التنظيف على أسماء الأعمدة في DataFrame
                df.columns = df.columns.str.strip() 
                
                # 2. استخراج الأسماء الفعلية للأعمدة بعد التنظيف للمقارنة
                actual_columns = df.columns.tolist()

                # 3. التحقق من وجود جميع الأعمدة الإلزامية المطلوبة
                if not all(col in actual_columns for col in REQUIRED_COLUMNS):
                    
                    required_str = ', '.join(REQUIRED_COLUMNS)
                    found_cols_str = ', '.join(actual_columns) if actual_columns else 'لم يتم العثور على أي أعمدة!'
                    
                    flash(f'فشل التحقق من الأعمدة. الملف يجب أن يحتوي على: {required_str} (مع عمود Time كاختياري).', 'danger')
                    flash(f'الأعمدة الفعلية التي تم العثور عليها هي: {found_cols_str}', 'danger')
                    
                    return redirect(request.url)
                
                # ----------------------------------------------------------------------
                
                processed_count = 0
                error_count = 0
                
                # التكرار على الصفوف وإضافة البيانات إلى الجلسة (Session)
                for index, row in df.iterrows():
                    student_zk_id = None 
                    attendance_time = None 

                    try:
                        # 1. استخراج الحقول الإلزامية 
                        student_zk_id = str(row['Student ZK ID']).strip()
                        date_data = row['Date'] 
                        number_fin = str(row['Number FIN']).strip()

                        # 2. معالجة التاريخ (إلزامي)
                        if isinstance(date_data, datetime):
                            attendance_date = date_data.date()
                        elif isinstance(date_data, str) and not date_data.strip():
                            raise ValueError("Date field is empty and mandatory.")
                        else:
                            attendance_date = pd.to_datetime(date_data).date()

                        # 3. معالجة الوقت (اختياري - يدعم NULL)
                        if 'Time' in actual_columns:
                            time_data = row['Time']

                            if pd.isna(time_data) or (isinstance(time_data, str) and not time_data.strip()):
                                attendance_time = None 
                            
                            elif isinstance(time_data, datetime_time):
                                attendance_time = time_data
                            
                            elif isinstance(time_data, datetime):
                                attendance_time = time_data.time()
                            
                            elif isinstance(time_data, str) and ':' in time_data:
                                attendance_time = datetime.strptime(str(time_data).strip(), '%H:%M').time()
                            
                            else:
                                raise ValueError(f"Time format is incorrect in row {index + 2}.")
                        
                        
                        # ----------------------------------------------------
                        # 🚀 منطق إدراج البيانات الفعلي (Attendance model)
                        # ----------------------------------------------------
                        # 🔴 ملاحظة للمستخدم: تأكد من أن 'Attendance' هو اسم الكلاس الصحيح للموديل.
                        new_record = Attendance(
                            student_zk_id=student_zk_id,
                            date=attendance_date, 
                            time=attendance_time,  # ستحفظ كـ NULL إذا كانت None
                            number_fin=number_fin
                        )
                        db.session.add(new_record)
                        
                        processed_count += 1
                        
                    except Exception as e:
                        # خطأ في معالجة صف معين - نراجع الجلسة ونحسب الخطأ
                        db.session.rollback() # 💡 مهم جداً: التراجع عن أي تغييرات فاشلة في هذا الصف
                        print(f"Error processing row {index + 2} (ID: {student_zk_id if student_zk_id else 'N/A'}): {e}")
                        error_count += 1
                        
                
                # ----------------------------------------------------
                # 💾 تنفيذ الالتزام (Commit) لحفظ جميع السجلات الناجحة دفعة واحدة
                # ----------------------------------------------------
                try:
                    if processed_count > 0:
                        db.session.commit() # 🚀 هنا يتم حفظ البيانات فعليًا في قاعدة البيانات
                        flash(f'تم رفع ومعالجة {processed_count} سجل حضور خام بنجاح.', 'success')
                    
                    if error_count > 0:
                        flash(f'حدثت أخطاء في {error_count} سجل (تحقق من تنسيق البيانات). لم يتم حفظ هذه السجلات.', 'warning')
                    
                    if processed_count == 0 and error_count == 0:
                         flash('لم يتم العثور على بيانات صالحة لمعالجتها في الملف.', 'warning')
                         db.session.rollback() # لا يوجد شيء للحفظ

                except Exception as e:
                    # فشل Commit كامل (على مستوى قاعدة البيانات)
                    db.session.rollback() 
                    flash(f'فشل حفظ البيانات في قاعدة البيانات: {e}', 'danger')
                    print(f"Database Commit Error: {e}")
                
                # ----------------------------------------------------
                
                return redirect(url_for('admin_attendance_entry'))
                
            except Exception as e:
                # خطأ عام في معالجة الملف
                flash(f'حدث خطأ غير متوقع أثناء معالجة الملف: {e}', 'danger')
                print(f"General file processing error: {e}") 
                return redirect(request.url)


    # GET request: عرض نموذج الرفع
    return render_template('attendance_upload_form.html', 
                           title='رفع بيانات الحضور الخام عبر Excel')
@app.route('/attendance/<zk_id>', methods=['GET', 'POST'])
def handle_attendance(zk_id):
    
    # 🛑 التعديل رقم 1: منطق التعامل مع طلب GET (جلب البيانات)
    if request.method == 'GET':
        try:
            # 🆕 التأكد أولاً من أن الطالب موجود
            student = Student.query.filter_by(zk_user_id=zk_id).first()
            if not student:
                 # إرجاع 404 إذا لم يتم العثور على الطالب
                 return jsonify({'message': f'Student with ZK ID {zk_id} not found'}), 404

            # استعلام لجلب جميع سجلات الحضور لهذا الطالب
            attendance_records = Attendance.query.filter_by(student_zk_id=zk_id).all()
            
            # تحويل البيانات إلى قائمة من القواميس قابلة للعرض
            results = []
            for record in attendance_records:
                # 🔑 منطق تحديد الحالة بناءً على وجود حقل الوقت (time) 🔑
                # إذا كان حقل الوقت موجوداً (ليس None)، فالحالة "present"
                # إذا كان حقل الوقت غير موجود (None)، فالحالة "absent"
                # نستخدم حقل الحالة المسجل في قاعدة البيانات كقيمة افتراضية إذا لم يكن الوقت محدداً بوضوح
                
                final_status = record.status # القيمة الافتراضية من قاعدة البيانات
                if record.time:
                    final_status = 'present'
                elif record.date and not record.time:
                    final_status = 'absent'
                
                results.append({
                    # 🛑 تحديث اسم العمود من columnid إلى id
                    'id': record.id,
                    # 🆕 استخدام .isoformat() لتحويل التاريخ والوقت إلى سلاسل صالحة
                    'date': record.date.isoformat(),
                    'time': record.time.isoformat() if record.time else None, 
                    # 🛑 إرسال الحالة المحددة ديناميكياً
                    'status': final_status, 
                    'number_fin': record.number_fin
                })
            
            # 🛑 التعديل الجديد: تغليف القائمة داخل كائن JSON باسم 'attendance'
            return jsonify({'attendance': results}), 200
            
        except Exception as e:
            # 🛑 طباعة الخطأ الذي ظهر في تتبع الخطأ السابق
            print(f"GET attendance error: {e}") 
            # 🛑 في حالة الخطأ الحقيقي نرجع 500
            return jsonify({'message': f'Error fetching attendance: {str(e)}'}), 500

    # 🛑 التعديل رقم 2: منطق التعامل مع طلب POST (إضافة/تحديث البيانات)
    elif request.method == 'POST':
        try:
            data = request.get_json()
            date_str = data.get('date')
            time_str = data.get('time') # 🆕 جلب حقل الوقت
            status = data.get('status') # 🛑 لم يعد هذا الحقل ضرورياً حقاً، لكن سنحتفظ به كاحتياطي
            number_fin = data.get('number_fin') # 🆕 جلب حقل FIN
            
            if not date_str:
                return jsonify({'message': 'Missing date'}), 400

            # 🔑 تحديد الحالة بناءً على الوقت قبل الحفظ
            # إذا أرسل العميل وقتاً، فإن الطالب حاضر
            # إذا لم يرسل وقتاً، فإن الطالب غائب (طالما أرسل تاريخاً)
            final_status_for_db = 'present' if time_str else 'absent'
            
            # التحقق من وجود الطالب
            student = Student.query.filter_by(zk_user_id=zk_id).first()
            if not student:
                return jsonify({'message': f'Student with ZK ID {zk_id} not found'}), 404

            # تحويل التاريخ والوقت
            try:
                # 🛑 التاريخ الآن يرسل إلى العمود المسمى 'date'
                attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # إذا كان هناك وقت، قم بتحويله
                attendance_time = None
                if time_str:
                    # نفترض تنسيق الوقت HH:MM:SS أو HH:MM
                    try:
                        attendance_time = datetime.strptime(time_str, '%H:%M:%S').time()
                    except ValueError:
                        attendance_time = datetime.strptime(time_str, '%H:%M').time()
                        
            except ValueError:
                return jsonify({'message': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM:SS or HH:MM for time.'}), 400

            # 🔑 التحقق من التكرار بناءً على zk_id والتاريخ فقط (القيد الجديد)
            existing_record = Attendance.query.filter_by(
                student_zk_id=zk_id,
                # 🛑 استخدام اسم العمود الجديد 'date'
                date=attendance_date
            ).first()

            if existing_record:
                # تحديث السجل الحالي
                existing_record.time = attendance_time # تحديث الوقت
                # 🛑 حفظ الحالة المحددة بناءً على الوقت المرسل
                existing_record.status = final_status_for_db 
                existing_record.number_fin = number_fin # تحديث رقم FIN
                db.session.commit()
                return jsonify({'message': f'Attendance updated for {zk_id} on {date_str}: {final_status_for_db}'}), 200
            else:
                # إنشاء سجل جديد
                new_record = Attendance(
                    student_zk_id=zk_id,
                    # 🛑 استخدام اسم العمود الجديد 'date'
                    date=attendance_date,
                    time=attendance_time, # 🆕 إضافة الوقت
                    # 🛑 حفظ الحالة المحددة بناءً على الوقت المرسل
                    status=final_status_for_db,
                    number_fin=number_fin # 🆕 إضافة رقم FIN
                )
                db.session.add(new_record)
                db.session.commit()
                return jsonify({'message': f'Attendance recorded for {zk_id} on {date_str}: {final_status_for_db}'}), 201

        except Exception as e:
            db.session.rollback()
            print(f"FATAL ERROR during POST attendance handling: {e}")
            return jsonify({'message': f'Internal Server Error: {str(e)}'}), 






@app.route('/admin/upload/attendance', methods=['GET', 'POST'])
def admin_upload_attendance():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('لم يتم اختيار ملف!', 'danger')
            return redirect(url_for('admin_upload_attendance'))
        
        file = request.files['excel_file']
        
        if file.filename == '':
            flash('لم يتم اختيار ملف!', 'danger')
            return redirect(url_for('admin_upload_attendance'))
        
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            try:
                df = pd.read_excel(BytesIO(file.read()))
                
                # 🔑 الأعمدة المطلوبة
                required_columns = ['student_zk_id', 'date', 'time', 'status', 'number_fin']
                if not all(col in df.columns for col in required_columns):
                    missing = [col for col in required_columns if col not in df.columns]
                    flash(f"الرجاء التأكد من وجود جميع الأعمدة المطلوبة في ملف الإكسل. الأعمدة الناقصة: {', '.join(missing)}", 'danger')
                    return redirect(url_for('admin_upload_attendance'))

                success_count = 0
                error_messages = []

                for index, row in df.iterrows():
                    try:
                        zk_id = str(row['student_zk_id']).strip()
                        
                        student = Student.query.filter_by(zk_user_id=zk_id).first()
                        if not student:
                            error_messages.append(f"السطر {index+2} (ZK ID: {zk_id}): لم يتم العثور على طالب.")
                            continue

                        # معالجة التاريخ والوقت
                        attendance_date = pd.to_datetime(row['date']).date()

                        time_value = row['time']
                        attendance_time = None
                        if pd.notna(time_value):
                            if isinstance(time_value, datetime_time):
                                attendance_time = time_value
                            # إذا كانت قيمة TimeStamp (من Excel)، نحولها إلى وقت Python
                            elif pd.notna(pd.to_datetime(time_value, errors='ignore')) and not isinstance(time_value, str):
                                attendance_time = pd.to_datetime(time_value).time()
                            else:
                                # محاولة تحويل سلسلة نصية أو رقمية
                                try:
                                    # نفترض تنسيق HH:MM:SS
                                    attendance_time = datetime.strptime(str(time_value).split('.')[0], '%H:%M:%S').time()
                                except:
                                    try:
                                        # نفترض تنسيق HH:MM
                                        attendance_time = datetime.strptime(str(time_value).split('.')[0], '%H:%M').time()
                                    except:
                                        # إذا فشل التحويل نتركها فارغة
                                        attendance_time = None


                        status = str(row['status']).strip()
                        number_fin = int(row['number_fin']) if pd.notna(row['number_fin']) and str(row['number_fin']).isdigit() else None
                        
                        existing_record = Attendance.query.filter_by(
                            student_zk_id=zk_id,
                            date=attendance_date
                        ).first()

                        if existing_record:
                            existing_record.time = attendance_time
                            existing_record.status = status
                            existing_record.number_fin = number_fin
                        else:
                            new_record = Attendance(
                                student_zk_id=zk_id,
                                date=attendance_date,
                                time=attendance_time,
                                status=status,
                                number_fin=number_fin
                            )
                            db.session.add(new_record)
                        
                        db.session.commit()
                        success_count += 1

                    except Exception as e:
                        db.session.rollback()
                        error_messages.append(f"السطر {index+2}: حدث خطأ في معالجة البيانات ({str(e)}).")
                        
                
                flash(f"تم رفع الملف بنجاح. تم معالجة {success_count} سجل.", 'success')
                if error_messages:
                    error_summary = "\n".join(error_messages[:5]) # عرض أول 5 أخطاء فقط
                    if len(error_messages) > 5:
                         error_summary += f"\n... و {len(error_messages) - 5} أخطاء أخرى."
                    flash("⚠️ حدثت بعض الأخطاء أثناء المعالجة:\n" + error_summary, 'warning')
                
                return redirect(url_for('admin_upload_attendance'))

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ غير متوقع أثناء قراءة الملف أو تنسيقه: {str(e)}', 'danger')
                return redirect(url_for('admin_upload_attendance'))
        else:
            flash('الرجاء رفع ملف بصيغة Excel (.xlsx أو .xls).', 'danger')
            return redirect(url_for('admin_upload_attendance'))

    return render_template('upload_form.html')
#______________________________________________________________________________________________________________________________________

class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_zk_id = db.Column(db.String(20), db.ForeignKey('students.zk_user_id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    month_name = db.Column(db.String(20), nullable=False)
    subject_name = db.Column(db.String(100), db.ForeignKey('subjects.name'), nullable=False)
    homework_grade = db.Column(db.Integer, default=0)
    oral_grade = db.Column(db.Integer, default=0)
    attendance_grade = db.Column(db.Integer, default=0)
    written_grade = db.Column(db.Integer, default=0)
   #total_grade = db.Column(db.Integer, default=0)
    final_total_grade = db.Column(db.Integer, default=0)
    result = db.Column(db.String(20), default='NA')

    __table_args__ = (
        UniqueConstraint('student_zk_id', 'academic_year', 'month_name', 'subject_name', name='_monthly_grade_uc'),
    )

class MidTermGrade(db.Model):
    __tablename__ = 'mid_term_grades'
    
    id = db.Column(db.Integer, primary_key=True) 
    
    student_zk_id = db.Column(db.String(50), db.ForeignKey('students.zk_user_id'), nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False) 
    term_total_grade = db.Column(db.Float, nullable=True, default=0.0)
    
    # 🛑 التعديل هنا: تغيير db.Float إلى db.Integer
    accumulated_grade = db.Column(db.Integer, default=0)
    end_term_grade = db.Column(db.Integer, default=0)
    term_total_grade = db.Column(db.Integer, default=0)
    
    result = db.Column(db.String(50), default='غير محدد')
    
    mid_term_ranking = db.Column(db.String(50), default='لم يحدد') 
    mid_term_result = db.Column(db.String(50), default='لم يحدد') 
    final_term_grade = db.Column(db.Integer, nullable=True, default=0) # المجموع الكلي اليدوي للتقرير
    
    __table_args__ = (
       db.UniqueConstraint('student_zk_id', 'subject_name', 'academic_year', name='_mid_term_grade_uc'),
    )
    
    def __repr__(self):
        return f'<MidTermGrade {self.student_zk_id} - {self.subject_name}>'

class FinalGrade(db.Model):
    __tablename__ = 'final_grades'
    id = db.Column(db.Integer, primary_key=True)
    student_zk_id = db.Column(db.String(20), db.ForeignKey('students.zk_user_id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    overall_total = db.Column(db.Integer, default=0)
    overall_ranking = db.Column(db.Integer, nullable=True)
    general_result = db.Column(db.String(20), default='NA')

    __table_args__ = (
        UniqueConstraint('student_zk_id', 'academic_year', name='_final_grade_uc'),
    )

# تأكد من استيراد هذه الدالة في بداية ملف app.py:
# from sqlalchemy import UniqueConstraint

class MonthlyGrade(db.Model):
    # 🔑 جدول قاعدة البيانات يجب أن يكون monthly_grades
    __tablename__ = 'monthly_grades' 
    id = db.Column(db.Integer, primary_key=True)
    student_zk_id = db.Column(db.String(20), db.ForeignKey('students.zk_user_id'), nullable=False)
    # ✅ التصحيح: استخدام عمود year
    year = db.Column(db.Integer, nullable=False) 
    month_name = db.Column(db.String(20), nullable=False)
    subject_name = db.Column(db.String(100), db.ForeignKey('subjects.name'), nullable=False)
    homework_grade = db.Column(db.Integer, default=0)
    oral_grade = db.Column(db.Integer, default=0)
    attendance_grade = db.Column(db.Integer, default=0)
    written_grade = db.Column(db.Integer, default=0)
    app=db.Column(db.Integer, default=0)
    supplies=db.Column(db.Integer, default=0)
    # ✅ التصحيح: استخدام عمود final_total_grade
    final_total_grade = db.Column(db.Integer, default=0) 
    result = db.Column(db.String(20), default='0')

    __table_args__ = (
        UniqueConstraint('student_zk_id', 'year', 'month_name', 'subject_name', name='_monthly_grade_uc'),
    )
    
    
    def __repr__(self):
        return f'<MonthlyGrade {self.student_zk_id} - {self.subject_name} {self.month_name}>'

# =========================================================
# 4. تهيئة Flask-Admin
# =========================================================

class SchoolAdminModelView(ModelView):
    # تم الإبقاء على هذا التصحيح: لحقن ملف CSS وإخفاء الشريط العلوي
    extra_css = ['/static/admin_custom.css']

    # تعيين لغة الواجهة إلى العربية (من اليمين لليسار)
    column_labels = dict(
        id='المعرف',
        name='الاسم',
        username='اسم المستخدم',
        password='كلمة المرور المشفرة', # تغيير التسمية لتوضيح أنها مشفرة
        role='الدور',
        zk_user_id='رقم ZK ID',
        parent_id='معرف ولي الأمر',
        class_id='معرف الصف',
        academic_year='العام الأكاديمي',
        next_class_id='الصف التالي',
        date='التاريخ',
        time='الوقت',
        status='الحالة',
        student_zk_id='ZK ID الطالب',
        month_name='الشهر',
        subject_name='المادة',
        homework_grade='واجب',
        oral_grade='شفوي',
        attendance_grade='حضور',
        written_grade='تحريري',
        total_grade='المجموع',
        accumulated_grade='درجات الشهور',
        end_term_grade='اختبار الفصل',
        term_total_grade='مجموع الفصل',
        result='النتيجة',
        overall_total='المجموع العام',
        overall_ranking='الترتيب العام',
        general_result='النتيجة العامة'
    )
    can_view_details = True
    page_size = 50
    column_display_pk = True

# 🆕 الفئات الإدارية المُصَحَّحة والمفقودة
class UserView(SchoolAdminModelView):

    # ✅ تحديد القوالب الأربعة (لإخفاء الأشرطة والتنسيق)
    list_template = 'admin/model/user_list.html'
    create_template = 'admin/model/user_create.html'
    edit_template = 'admin/model/user_edit.html'
    details_template = 'admin/model/user_details.html'

    # تفعيل النوافذ المنبثقة والبحث باسم الطالب
    create_modal = True
    edit_modal = True

    column_searchable_list = (
        'username',
        'role',
        'students.name', # البحث باسم الطالب
    )

    # دالة لعرض أسماء الطلاب
    def _list_student_names(view, context, model, name):
        student_names = [student.name for student in model.students]
        return ", ".join(student_names) if student_names else "لا يوجد"

    column_formatters = {
        'students': _list_student_names
    }

    # تعيين التسميات العربية لحقول الإدخال
    form_args = {
        'username': {'label': 'اسم المستخدم'},
        'role': {'label': 'الدور'},
    }

    # إضافة حقل إدخال كلمة المرور مع تسمية عربية
    form_extra_fields = {
        'password_hash': fields.PasswordField('كلمة المرور (تعديل/إنشاء)', widget=PasswordInput(), validators=[validators.Optional()])
    }

    column_list = ('username', 'role', 'students', 'id')
    column_exclude_list = ('password',)
    form_excluded_columns = ('password', 'students')

    def on_model_change(self, form, model, is_created):
        if 'password_hash' in form and form.password_hash.data:
            model.password = generate_password_hash(form.password_hash.data)

        if is_created and not model.role:
            model.role = 'parent'

        super(UserView, self).on_model_change(form, model, is_created)

    # تعريب الأعمدة وأزرار الإجراءات
    column_labels = SchoolAdminModelView.column_labels.copy()
    column_labels.update({
        'students': 'أسماء الأبناء',
        'username': 'اسم المستخدم',
        'role': 'الدور',
        'edit_modal': 'تعديل',
        'delete_modal': 'حذف',
        'details_modal': 'تفاصيل'
    })

    # تعريب العناوين الرئيسية
    name = 'المستخدمون'
    name_plural = 'إدارة أولياء الأمور'
    endpoint = 'user' # يجب أن يكون هذا آخر سطر إعدادي تقريباً


    # ✅✅✅ تحديد القوالب الأربعة (كما هي)

class StudentView(SchoolAdminModelView):
    column_list = ('name', 'zk_user_id', 'current_class', 'parent', 'id')

    # 🆕 تعيين التسميات العربية لحقول الإدخال في نموذج الطالب
    form_args = {
        'name': {'label': 'اسم الطالب'},
        'zk_user_id': {'label': 'رقم الهوية (ZK ID)'},
        'current_class': {'label': 'الصف الحالي'},
        'parent': {'label': 'ولي الأمر'}, # هذا الحقل يعرض علاقة User
    }

    # 🆕 تحديث تسميات الأعمدة في الجدول
    column_labels = SchoolAdminModelView.column_labels.copy()
    column_labels.update({
        'name': 'الاسم',
        'zk_user_id': 'رقم ZK ID',
        'current_class': 'الصف الحالي',
        'parent': 'ولي الأمر'
    })
    column_searchable_list = ('name', 'zk_user_id')
    column_filters = ('current_class.name', 'parent.username')

class ClassView(SchoolAdminModelView):
    column_list = ('name', 'academic_year', 'next_class', 'students', 'id')
    column_labels = SchoolAdminModelView.column_labels.copy()
    column_labels.update({'next_class': 'الصف التالي', 'students': 'الطلاب'})
    column_searchable_list = ('name',)
    column_filters = ('academic_year',)

class SubjectView(SchoolAdminModelView):
    column_list = ('name', 'id')
  


class GradeView(SchoolAdminModelView):
    column_list = ('student_zk_id', 'academic_year', 'month_name', 'subject_name', 'homework_grade', 'oral_grade', 'attendance_grade', 'written_grade', 'total_grade', 'result')
    column_labels = SchoolAdminModelView.column_labels.copy()
    column_labels.update(dict(
        student='الطالب', student_zk_id='ZK ID الطالب', academic_year='السنة', month_name='الشهر', subject_name='المادة', homework_grade='واجب', oral_grade='شفوي', attendance_grade='حضور', written_grade='تحريري', total_grade='المجموع الشهري', result='النتيجة'
    ))
    column_searchable_list = ('student_zk_id', 'academic_year', 'month_name', 'subject_name')
    column_filters = ('academic_year', 'month_name', 'subject_name')


class ReadOnlyGradeView(SchoolAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False


# ---------------------------------------------------------
# 7. تهيئة Flask-Admin
# ---------------------------------------------------------

admin = Admin(app, name='لوحة تحكم النظام', url='/admin/dashboard')

admin.add_view(UserView(User, db.session, name='إدارة المستخدمين'))
admin.add_view(StudentView(Student, db.session, name='إدارة الطلاب'))
admin.add_view(ClassView(Class, db.session, name='إدارة الصفوف'))
admin.add_view(SubjectView(Subject, db.session, name='إدارة المواد'))
admin.add_view(AttendanceView(Attendance, db.session, name='سجلات الحضور'))
admin.add_view(GradeView(Grade, db.session, name='الدرجات الشهرية'))
admin.add_view(ReadOnlyGradeView(MidTermGrade, db.session, name='النتائج النصفية'))
admin.add_view(ReadOnlyGradeView(FinalGrade, db.session, name='النتائج النهائية'))

# =========================================================
# 5. دوال مساعدة (Helper Functions)
# =========================================================
# ... (باقي الدوال والمسارات كما هي)
# ...
def get_current_year():
    """الحصول على السنة الأكاديمية الحالية."""
    return datetime.now(YEMEN_TZ).year

def calculate_monthly_result(total_grade, subject_name):
    """تحديد نتيجة الطالب (ناجح/راسب) بناءً على مجموع الدرجات الشهرية."""
    if total_grade >= 60:
        return 'ناجح'
    else:
        return 'راسب'

def calculate_mid_term_result(total_grade, subject_name):
    """تحديد نتيجة الطالب (ناجح/راسب) بناءً على مجموع الدرجات النصفية."""
    if total_grade >= 60:
        return 'ناجح'
    else:
        return 'راسب'


# =========================================================
# 6. مسارات API (Routes)
# =========================================================

# ------------------------------------------
# 6.1 مسارات الإدارة (Admin Routes)
# ------------------------------------------

# 🛑 تم إنشاء نقطة نهاية باسم 'admin_dashboard' ليتطابق مع ما تم تصحيحه في قالب زر الرجوع
@app.route('/admin/dashboard', endpoint='admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html',
                            student_count=db.session.query(Student).count(),
                            class_count=db.session.query(Class).count(),
                            subject_count=db.session.query(Subject).count())

@app.route('/admin/reports')
def admin_reports():
    return render_template('reports_page.html')


def get_year():
    
   
   
    return datetime.now().year

@app.route('/admin/grades/monthly')
@login_required
def admin_grade_entry_form():
    """
    عرض نموذج إدخال الدرجات الشهرية (لإدخال درجة طالب واحد لمادة وشهر محددين).
    """
    
    # 1. جلب جميع الطلاب لخاصية البحث (datalist)
    try:
        students = db.session.query(Student).order_by(Student.name).all()
    except OperationalError as e:
        # في حال لم يتم إنشاء الجداول بعد
        print(f"Database Operational Error: {e}")
        flash("خطأ في الاتصال بقاعدة البيانات. تأكد من إنشاء الجداول.", 'danger')
        students = [] 

    # 2. تحديد التاريخ والوقت الحاليين للمنطقة الزمنية (للقيم الافتراضية)
    tz = pytz.timezone(TIMEZONE)
    current_time_tz = datetime.now(tz)
    
    # 3. قائمة بأسماء الأشهر باللغة العربية (مطابقة لما يتوقعه القالب)
    ARABIC_MONTHS = [
        (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'), 
        (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'), 
        (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
    ]
    
    # 4. تمرير البيانات إلى القالب
    return render_template('admin_grade_entry_form.html',
        students=students,
        now=current_time_tz,
        months=ARABIC_MONTHS, # يستخدم لتعيين القيمة الافتراضية للشهر
    )


@app.route('/admin/grades/import_excel', methods=['POST'])
def admin_grade_import_excel():
    """
    Handles the import of monthly grades from an uploaded Excel file.
    🔑 تم تعديلها لتتوافق مع Schema الجديد:
       - استخدام student_zk_id (VARCHAR) بدلاً من student_id (INTEGER).
       - استخدام month_name (VARCHAR) بدلاً من month (INTEGER).
       - استيراد الدرجات الفرعية وحساب final_total_grade.
    """
    # 1. Check for file upload
    if 'excel_file' not in request.files:
        flash('لم يتم رفع أي ملف.', 'danger')
        return redirect(url_for('admin_grade_entry_form'))

    file = request.files['excel_file']
    if file.filename == '':
        flash('لم يتم تحديد ملف.', 'danger')
        return redirect(url_for('admin_grade_entry_form'))

    # 2. Validate file type (.xlsx or .xls)
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        flash('تنسيق الملف غير مدعوم. يرجى رفع ملف Excel بصيغة .xlsx أو .xls.', 'danger')
        return redirect(url_for('admin_grade_entry_form'))

    # 3. Process the file
    try:
        # Read Excel file into a pandas DataFrame
        df = pd.read_excel(file)

        # 🔑 الأعمدة المطلوبة الجديدة
        required_cols = [
            'student_zk_id', 
            'subject_name', 
            'month_name', 
            'year', 
            'homework_grade', 
            'oral_grade', 
            'attendance_grade', 
            'written_grade',
            'app',
            'supplies'
        ]
        
        # التأكد من وجود جميع الأعمدة المطلوبة
        if not all(col in df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df.columns]
            flash(f"ملف Excel يجب أن يحتوي على جميع الأعمدة التالية: {', '.join(required_cols)}. الأعمدة المفقودة: {', '.join(missing_cols)}", 'danger')
            return redirect(url_for('admin_grade_entry_form'))

        imported_count = 0
        skipped_count = 0
        
        # تجهيز قائمة بأسماء الشهور للتحقق إذا لزم الأمر (اختياري)
        # month_names = [m[1] for m in ARABIC_MONTHS] 

        for index, row in df.iterrows():
            try:
                # 4. استخراج البيانات والتحويل الآمن للأنواع
                zk_user_id = str(row['student_zk_id']).strip() # رقم الطالب (VARCHAR)
                subject_name = str(row['subject_name']).strip()
                month_name = str(row['month_name']).strip() # اسم الشهر النصي (VARCHAR)
                year = int(row['year'])
                
                # الدرجات الفرعية (تحويل آمن إلى عدد صحيح)
                homework_grade = int(row.get('homework_grade', 0))
                oral_grade = int(row.get('oral_grade', 0))
                attendance_grade = int(row.get('attendance_grade', 0))
                written_grade = int(row.get('written_grade', 0))
                app=int(row.get('app', 0))
                supplies=int(row.get('supplies', 0))
                # حساب الدرجة الكلية (final_total_grade)
                final_total_grade = homework_grade + oral_grade + attendance_grade + written_grade+app
                
                # حساب النتيجة
                result = "ناجح" if final_total_grade >= 50 else "راسب" # (يمكن تعديل المعيار حسب الحاجة)

                # التحقق من القيم الأساسية
                if not all([zk_user_id, subject_name, month_name, year]):
                    skipped_count += 1
                    flash(f"تم تخطي السطر {index + 2}: قيم أساسية مفقودة.", 'warning')
                    continue

                # 5. البحث عن الطالب باستخدام zk_user_id
                student = db.session.query(Student).filter_by(zk_user_id=zk_user_id).first()
                if not student:
                    skipped_count += 1
                    flash(f"تم تخطي السطر {index + 2}: لم يتم العثور على طالب بالرقم التعريفي {zk_user_id}.", 'warning')
                    continue

                # 6. البحث عن الدرجة الموجودة (للتحديث)
                # 🔑 الاستعلام الآن يستخدم student_zk_id, month_name, subject_name
                grade = db.session.query(MonthlyGrade).filter_by(
                    student_zk_id=zk_user_id,
                    subject_name=subject_name,
                    month_name=month_name,
                    year=year
                ).first()


                if grade:
                    # تحديث الدرجة الموجودة
                    grade.final_total_grade = final_total_grade
                    grade.homework_grade = homework_grade
                    grade.oral_grade = oral_grade
                    grade.attendance_grade = attendance_grade
                    grade.written_grade = written_grade
                    grade.result = result
                    grade.app=app
                    grade.supplies=supplies
                else:
                    # إنشاء درجة جديدة
                    new_grade = MonthlyGrade(
                        student_zk_id=zk_user_id,
                        subject_name=subject_name,
                        month_name=month_name,
                        year=year,
                        final_total_grade=final_total_grade,
                        homework_grade=homework_grade,
                        oral_grade=oral_grade,
                        attendance_grade=attendance_grade,
                        written_grade=written_grade,
                        result=result,
                        app=app,
                        supplies=supplies,
                    )
                    db.session.add(new_grade)

                imported_count += 1

            except ValueError:
                skipped_count += 1
                flash(f"تم تخطي السطر {index + 2}: خطأ في نوع البيانات (تأكد من أن year والدرجات الفرعية أرقام).", 'warning')
            except Exception as e_row:
                skipped_count += 1
                current_app.logger.error(f"Error processing row {index + 2}: {e_row}")
                flash(f"تم تخطي السطر {index + 2} بسبب خطأ غير متوقع: {str(e_row)}.", 'warning')


        db.session.commit()
        flash(f'✅ تم استيراد {imported_count} درجة بنجاح. تم تخطي {skipped_count} سجل بسبب أخطاء.', 'success')

        
        # 7. الالتزام بالبيانات في قاعدة البيانات
        # ⚠️ إذا حدث خطأ قبل الـ commit، فإننا نقوم بالـ rollback في البلوك except الذي يليه
        db.session.commit()
        current_app.logger.info(f"DB commit successful. Imported: {imported_count}, Skipped: {skipped_count}")
        flash(f'✅ تم استيراد {imported_count} درجة بنجاح. تم تخطي {skipped_count} سجل بسبب أخطاء.', 'success')


    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Critical error during grade import: {e}")
        flash(f'❌ حدث خطأ فادح أثناء استيراد الدرجات. يرجى التحقق من تنسيق الملف: {e}', 'danger')
        
    return redirect(url_for('admin_grade_entry_form'))



#==================================================================================
@app.route('/admin/grades/mid_term')
def admin_mid_term_entry_form():
    students = db.session.query(Student.name, Student.zk_user_id).all()
    
    # 🛑 الحل هنا: تحويل قائمة الـ Tuples إلى قائمة نصوص بسيطة 🛑
    raw_subjects = db.session.query(Subject.name).all()
    subjects = [s[0] for s in raw_subjects] # استخراج النص من داخل الـ tuple
    
    current_year = get_current_year()
    return render_template('mid_term_entry_form.html',
                           students=students,
                           subjects=subjects,
                           current_year=current_year)


import pandas as pd
import io
from flask import request, jsonify

@app.route('/api/grades/mid_term/save', methods=['POST'])
def save_mid_term_grade():
    try:
        # --- الجزء الأول: تحديد مصدر البيانات (ملف أم JSON) ---
        all_data_to_process = []
        is_bulk_upload = False

        # إذا كان الطلب يحتوي على ملف (رفع ملف CSV)
        if 'file' in request.files:
            is_bulk_upload = True
            file = request.files['file']
            if file.filename == '':
                return jsonify({"success": False, "message": "لم يتم اختيار ملف"}), 400
            
            # قراءة الملف ومعالجة الترميز العربي
            content = file.read()
            try:
                df = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig')
            except:
                df = pd.read_csv(io.BytesIO(content), encoding='cp1256')
            
            # تحويل DataFrame إلى قائمة قواميس (JSON-like) لتعاملها بنفس منطق الكود الأصلي
            all_data_to_process = df.to_dict(orient='records')
        
        # إذا كان الطلب JSON (إدخال يدوي من الفورم)
        else:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "message": "لا توجد بيانات مستلمة"}), 400
            all_data_to_process = [data] # نضعه في قائمة لتوحيد المعالجة

        # --- الجزء الثاني: منطق المعالجة الأساسي (نفس كودك الأصلي) ---
        results_summary = {"success_count": 0, "errors": []}

        for entry in all_data_to_process:
            try:
                zk_id = entry.get('student_zk_id')
                year = entry.get('academic_year')
                subject_name = entry.get('subject_name')

                # التحقق الحاسم من معرف الطالب
                if zk_id is None or str(zk_id).strip() == "" or str(zk_id).lower() == "none":
                    if not is_bulk_upload:
                        return jsonify({"success": False, "message": "معرف الطالب مطلوب"}), 400
                    continue # في حالة الملف نتخطى الصفوف الفارغة

                # تنظيف اسم المادة
                if isinstance(subject_name, str):
                    subject_name = subject_name.replace("('", "").replace("',)", "").strip()
                else:
                    subject_name = "غير محدد"

                # دالة تنظيف الأرقام (من كودك الأصلي)
                def clean_int(val):
                    try:
                        if pd.isna(val): return 0 # معالجة قيم NaN في الجداول
                        return int(float(val)) if val is not None else 0
                    except:
                        return 0

                accumulated_grade = clean_int(entry.get('accumulated_grade'))
                end_term_grade = clean_int(entry.get('end_term_grade'))
                total_grade = accumulated_grade + end_term_grade
                
                # حساب النتيجة
                res_val = entry.get('result')
                if not res_val or str(res_val) == "nan" or res_val == "None":
                    res_val = calculate_mid_term_result(total_grade, subject_name)

                # البحث عن سجل موجود مسبقاً (UPSERT)
                mid_term_grade = MidTermGrade.query.filter_by(
                    student_zk_id=str(zk_id).split('.')[0], # تنظيف المعرف من أي كسور
                    academic_year=str(year) if year and str(year) != "nan" else "2025",
                    subject_name=subject_name
                ).first()

                if mid_term_grade:
                    # تحديث السجل الحالي
                    mid_term_grade.accumulated_grade = accumulated_grade
                    mid_term_grade.end_term_grade = end_term_grade
                    mid_term_grade.term_total_grade = total_grade
                    mid_term_grade.result = res_val
                else:
                    # إنشاء سجل جديد
                    new_grade = MidTermGrade(
                        student_zk_id=str(zk_id).split('.')[0],
                        academic_year=str(year) if year and str(year) != "nan" else "2025",
                        subject_name=subject_name,
                        accumulated_grade=accumulated_grade,
                        end_term_grade=end_term_grade,
                        term_total_grade=total_grade,
                        result=res_val,
                        mid_term_ranking=entry.get('mid_term_ranking', 'لم يحدد'),
                        mid_term_result=entry.get('mid_term_result', 'لم يحدد'),
                        final_term_grade=clean_int(entry.get('final_term_grade'))
                    )
                    db.session.add(new_grade)
                
                results_summary["success_count"] += 1

            except Exception as row_err:
                results_summary["errors"].append(str(row_err))
                continue

        db.session.commit()

        # الاستجابة بناءً على نوع العملية
        if is_bulk_upload:
            return jsonify({
                "success": True, 
                "message": f"تمت معالجة الملف: تم حفظ/تحديث {results_summary['success_count']} سجل."
            }), 200
        else:
            return jsonify({
                "success": True, 
                "message": f"تمت العملية بنجاح للطالب {all_data_to_process[0].get('student_zk_id')}", 
                "total_grade": total_grade
            }), 200

    except Exception as e:
        db.session.rollback()
        print(f"CRITICAL ERROR: {str(e)}")
        return jsonify({
            "success": False, 
            "message": "حدث خطأ أثناء المعالجة", 
            "detail": str(e)
        }), 500

@app.route('/api/grades/mid_term/upload', methods=['POST'])
def upload_mid_term_grades():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "لم يتم العثور على ملف في الطلب"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "اسم الملف فارغ"}), 400
    
    try:
        # 1. قراءة البيانات الخام
        content = file.read()
        
        # 2. محاولة القراءة بأكثر من ترميز لضمان دعم العربية و Excel
        try:
            df = pd.read_csv(io.BytesIO(content), dtype=str, encoding='utf-8-sig')
        except:
            try:
                df = pd.read_csv(io.BytesIO(content), dtype=str, encoding='cp1256') # ترميز ويندوز العربي
            except:
                df = pd.read_csv(io.BytesIO(content), dtype=str)

        # 3. تنظيف شامل للأعمدة (إزالة المسافات، الرموز الغريبة، والتحويل لنصوص)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # تسجيل الأعمدة التي تم العثور عليها للمساعدة في التصحيح
        print(f"Detected Columns: {list(df.columns)}")

        # 4. استراتيجية تحديد الأعمدة (بالاسم أو بالموقع كخطة بديلة)
        # سنحاول إيجاد العمود الذي يحتوي على كلمة 'id' أو 'student' أو سنأخذ العمود الأول رقم 0
        
        def get_col_data(possible_names, index_fallback):
            for name in possible_names:
                if name in df.columns:
                    return df[name]
            return df.iloc[:, index_fallback] # إذا لم يجد الاسم، يأخذ العمود حسب ترتيبه

        # تعيين البيانات للأعمدة الأساسية
        student_ids = get_col_data(['student_zk_id', 'id', 'معرف الطالب', 'رقم الطالب'], 0)
        acc_grades = get_col_data(['accumulated_grade', 'أعمال السنة', 'الدرجة التراكمية'], 1)
        end_grades = get_col_data(['end_term_grade', 'درجة الترم', 'نهاية الترم'], 2)
        subject_names = get_col_data(['subject_name', 'المادة', 'اسم المادة'], 9) # حسب ملفك غالباً هو الأخير
        years = get_col_data(['academic_year', 'السنة الدراسية'], 8)

        success_count = 0
        error_details = []

        # 5. دوران المعالجة
        for i in range(len(df)):
            try:
                # تنظيف المعرف (إزالة الفواصل العشرية الناتجة عن إكسل)
                raw_sid = str(student_ids.iloc[i]).strip()
                if not raw_sid or raw_sid.lower() in ['nan', 'none', '']:
                    continue
                
                sid = raw_sid.split('.')[0]
                subj = str(subject_names.iloc[i]).strip() if i < len(subject_names) else "عام"
                year = str(years.iloc[i]).strip() if i < len(years) else "2025"

                # تحويل الدرجات
                def to_int(val):
                    try: return int(float(str(val).strip() or 0))
                    except: return 0

                acc = to_int(acc_grades.iloc[i])
                end = to_int(end_grades.iloc[i])
                
                # البحث عن سجل موجود أو إنشاء جديد
                grade_record = MidTermGrade.query.filter_by(
                    student_zk_id=sid,
                    subject_name=subj,
                    academic_year=year
                ).first()

                if grade_record:
                    grade_record.accumulated_grade = acc
                    grade_record.end_term_grade = end
                    grade_record.term_total_grade = acc + end
                else:
                    new_grade = MidTermGrade(
                        student_zk_id=sid,
                        subject_name=subj,
                        academic_year=year,
                        accumulated_grade=acc,
                        end_term_grade=end,
                        term_total_grade=acc + end,
                        result="ناجح" # افتراضي
                    )
                    db.session.add(new_grade)
                
                success_count += 1
                
                # تنفيذ الحفظ كل 50 سجل لسرعة الأداء وتقليل الضغط
                if success_count % 50 == 0:
                    db.session.commit()

            except Exception as row_e:
                error_details.append(f"السطر {i+2}: {str(row_e)}")

        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"تم بنجاح رفع {success_count} سجل.",
            "errors": error_details[:10] # إظهار أول 10 أخطاء فقط إن وجدت
        }), 200

    except Exception as global_e:
        db.session.rollback()
        print(f"Global Upload Error: {str(global_e)}")
        return jsonify({"success": False, "message": f"خطأ في قراءة هيكل الملف: {str(global_e)}"}), 500


@app.route('/admin/search/mid_term', methods=['GET'])
def admin_search_mid_term_grades():
    
    # 🛑🛑 الإضافة أو التصحيح هنا: يجب تعريف المتغير current_year 🛑🛑
    current_year = get_current_year() 
    
    # 1. جلب بيانات الطلاب (افترضنا أنك تستخدم هذه الطريقة)
    # تأكد من استيراد Student و db
    students_data = db.session.query(Student.name, Student.zk_user_id).order_by(Student.name).all()
    
    # 2. جلب الأعوام الأكاديمية المتاحة (يمكنك تعديل هذه الطريقة لجلبها من قاعدة البيانات)
    academic_years = list(range(current_year, current_year - 5, -1))

    # 3. تمرير المتغيرات المطلوبة للقالب
    return render_template(
        'search_mid_term_grades.html',
        students=students_data,
        academic_years=academic_years,
        current_year=current_year 
    )

                           



@app.route('/admin/search/mid_term/results', methods=['GET'])
# 🛑 تغيير اسم الدالة ليطابق ما تقترحه Flask
def view_mid_term_grades():
    # 1. جلب متغيرات البحث من الرابط (Query Parameters)
    zk_id = request.args.get('zk_id')
    year = request.args.get('year', type=int)

    if not zk_id or not year:
        # إذا لم يتم تمرير المتغيرات، أعد التوجيه أو عرض خطأ
        return redirect(url_for('admin_search_mid_term_grades'))

    # 2. جلب اسم الطالب (للعرض في رأس الجدول)
    student = Student.query.filter_by(zk_user_id=zk_id).first()
    student_name = student.name if student else "طالب غير معروف"

    # 3. جلب جميع الدرجات النصفية للطالب في هذا العام
    # 🛑 تأكد أن اسم الجدول هنا صحيح (MidTermGrade)
    grades = MidTermGrade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year
    ).order_by(MidTermGrade.subject_name).all()

    # 4. تمرير النتائج إلى القالب
    return render_template(
        'view_mid_term_grades.html',
        grades=grades, # 🛑 هذا هو المتغير الذي يجب أن يكون في القالب
        student_name=student_name,
        academic_year=year
    )


@app.route('/admin/export/mid_term/excel', methods=['GET'])
def export_mid_term_grades_to_excel():
    zk_id = request.args.get('zk_id')
    year = request.args.get('year', type=int)

    if not zk_id or not year:
        return jsonify({"error": "معلمات البحث مفقودة."}), 400

    # 1. جلب البيانات من قاعدة البيانات (نفس الاستعلام المستخدم للعرض)
    grades_objects = MidTermGrade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year
    ).order_by(MidTermGrade.subject_name).all()

    # 2. جلب اسم الطالب للعنوان واسم الملف
    student = Student.query.filter_by(zk_user_id=zk_id).first()
    student_name = student.name if student else "طالب_غير_معروف"
    
    if not grades_objects:
        return jsonify({"error": f"لا توجد درجات نصفية للطالب {student_name} في العام {year}."}), 404

    # 3. تحويل بيانات SQLAlchemy إلى قاموس/قائمة لتسهيل تحويلها إلى DataFrame
    data_list = []
    for grade in grades_objects:
        data_list.append({
            'المادة الدراسية': grade.subject_name,
            'الدرجة المتراكمة': grade.accumulated_grade,
            'درجة الاختبار النصفي': grade.end_term_grade,
            'المجموع الكلي': grade.term_total_grade, # استخدم term_total_grade
            'النتيجة': grade.result
        })

    # 4. إنشاء DataFrame باستخدام Pandas
    df = pd.DataFrame(data_list)

    # 5. تجهيز ملف Excel في الذاكرة (بدلاً من حفظه على القرص)
    output = BytesIO()
    # استخدام openpyxl كـ engine إذا كنت تحتاج صيغة .xlsx الأحدث
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: 
        # كتابة البيانات إلى ورقة Excel
        df.to_excel(writer, sheet_name=f'الدرجات النصفية - {year}', index=False)
        
        # يمكنك إضافة تنسيقات إضافية هنا إذا أردت

    output.seek(0) # العودة إلى بداية الملف

    # 6. إرسال الملف إلى المتصفح
    filename = f'تقرير_الدرجات_النصفية_{student_name}_{year}.xlsx'
    
    return send_file(output, 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=filename)
    
#=========================================================================================
class FinalSubjectGrade(db.Model):
    __tablename__ = 'final_subject_grades' 
    
    # 🔑 المفتاح الأساسي يجب أن يكون موجوداً
    id = db.Column(db.Integer, primary_key=True) 
    
    # حقول الارتباط
    student_zk_id = db.Column(db.String(20), db.ForeignKey('students.zk_user_id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)

    # حقول الدرجات
    first_acc_grade = db.Column(db.Float, default=0)
    first_acc_result = db.Column(db.Float, default=0) 
    second_acc_grade = db.Column(db.Float, default=0)
    second_acc_result = db.Column(db.Float, default=0)
    subject_total = db.Column(db.Float, default=0)
    
    # الحقول المدخلة يدوياً
    general_result = db.Column(db.String(50), default='لم يحدد')
    overall_ranking = db.Column(db.String(50), default='لم يحدد')
    
    __table_args__ = (
        UniqueConstraint('student_zk_id', 'academic_year', 'subject_name', name='_final_subject_grade_uc'),
    )
    
    def __repr__(self):
        return f"<FinalSubjectGrade {self.student_zk_id} - {self.subject_name} {self.academic_year}>"
   #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ 

@app.route('/admin/search/final', methods=['GET', 'POST'])
def admin_search_final_grades():
    # هذا هو الكود الكامل الذي يجب أن يكون موجوداً
    if request.method == 'POST':
        zk_id = request.form.get('zk_id')
        year = request.form.get('year')
        
        if zk_id and year:
            return redirect(url_for('admin_view_final_grades', zk_id=zk_id, year=year))
        else:
            # تحتاج هنا إلى تمرير المتغيرات المطلوبة للقالب
            students = db.session.query(Student.name, Student.zk_user_id).all()
            academic_years = db.session.query(FinalGrade.academic_year).distinct().order_by(FinalGrade.academic_year.desc()).all()
            academic_years = [str(year[0]) for year in academic_years]
            current_year = str(get_current_year())
            if current_year not in academic_years:
                academic_years.insert(0, current_year)
            
            return render_template('search_final_grades.html',
                                   students=students,
                                   academic_years=academic_years,
                                   current_year=current_year,
                                   search_results={"error": "الرجاء اختيار الطالب والعام الأكاديمي بشكل صحيح."})
    
    # جلب بيانات الطلاب والأعوام لعرضها في نموذج البحث
    students = db.session.query(Student.name, Student.zk_user_id).all()
    academic_years = db.session.query(FinalGrade.academic_year).distinct().order_by(FinalGrade.academic_year.desc()).all()
    academic_years = [str(year[0]) for year in academic_years]
    current_year = str(get_current_year())
    if current_year not in academic_years:
        academic_years.insert(0, current_year)
    
    return render_template('search_final_grades.html',
                           students=students,
                           academic_years=academic_years,
                           current_year=current_year,
                           search_results=None)



@app.route('/admin/view/final/<string:zk_id>/<int:year>')
def admin_view_final_grades(zk_id, year):
    
    student = Student.query.filter_by(zk_user_id=zk_id).first()
    if not student:
        return "الطالب غير موجود", 404

    # 1. جلب النتيجة النهائية العامة (Overall Final Grade)
    final_grade_record = FinalGrade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year
    ).first()



    # 2. جلب درجات المواد النهائية
    subject_grades = FinalSubjectGrade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year
    ).order_by(FinalSubjectGrade.subject_name).all()
    
    # 3. حساب المجموع الكلي للمواد (لتأكيد المجموع)
    
    # 🔑 التعديل هنا: حلقة لضمان أن كل مادة لديها subject_total
    # نمر على كل سجل مادة، وإذا كان subject_total هو None أو 0، نقوم بإعادة حسابه
    # من مجموع المحصلات الأربعة المتاحة، لضمان صحة العرض.
    for grade in subject_grades:
        if not grade.subject_total:
            grade.subject_total = (
                (grade.first_acc_grade or 0) +
                (grade.first_acc_result or 0) +
                (grade.second_acc_grade or 0) +
                (grade.second_acc_result or 0)
            )
            
    # حساب المجموع الكلي النهائي من القيم (المحسوبة أو المخزنة)
    # نستخدم (g.subject_total or 0) للتعامل مع أي حالات None متبقية
    calculated_total = sum(g.subject_total or 0 for g in subject_grades) 
    
    # 4. إرسال البيانات إلى القالب
    return render_template('view_final_grades.html',
                            student_name=student.name,
                            zk_id=zk_id,
                            year=year,
                            final_grade=final_grade_record, # يحتوي على overall_total, ranking, general_result
                            subject_grades=subject_grades,  # درجات المواد النهائية
                            calculated_total=calculated_total
                            )


class FinalStudentResult(db.Model):
    __tablename__ = 'final_student_results'  # 👈 يجب أن تبدأ بمسافة بادئة
    id = db.Column(db.Integer, primary_key=True)
    # اسم الطالب (ZK ID)
    student_zk_id = db.Column(db.String(20), db.ForeignKey('students.zk_user_id'), nullable=False)
    # العام الأكاديمي
    academic_year = db.Column(db.Integer, nullable=False)
    
    # المجموع الكلي للمواد
    overall_total_grade = db.Column(db.Float, default=0)
    
    # الترتيب (يتم تحديثه لاحقاً بعد حساب كل الطلاب)
    ranking = db.Column(db.Integer, nullable=True)
    
    # النتيجة العامة (ناجح/راسب/مرحل/يحتاج إعادة)
    general_result = db.Column(db.String(50), default='قيد الانتظار')
    
    __table_args__ = (
        UniqueConstraint('student_zk_id', 'academic_year', name='_final_student_result_uc'),
    )

    def __repr__(self):
        return f"<FinalStudentResult {self.student_zk_id} - {self.academic_year} - {self.general_result}>"
    




    @app.route('/admin/grades/final/entry', methods=['GET'])
    def admin_final_grade_entry_form():
    # جلب البيانات الأساسية (الطلاب، المواد، الأعوام)
     students = db.session.query(Student.name, Student.zk_user_id).order_by(Student.name).all()
     subjects = Subject.query.order_by(Subject.name).all()
     current_year = get_current_year() 
     academic_years = list(range(current_year, current_year - 5, -1))
    
     return render_template(
        'final_grade_entry_form.html',
        students=students,
        subjects=subjects,
        academic_years=academic_years
    
    )


    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
from datetime import datetime
@app.route('/final_report/<zk_id>', methods=['GET'])
def final_report(zk_id):
    requested_year = request.args.get('year', type=int)
    if not requested_year:
      academic_year_to_query = datetime.now().year
    else:
     academic_year_to_query = requested_year
    
    student = Student.query.filter_by(zk_user_id=zk_id).first()
    if not student:
        return jsonify({'message': 'Student not found'}), 404

    # 1. الاستعلام عن الدرجات
    grades = FinalSubjectGrade.query.filter(
        FinalSubjectGrade.student_zk_id == zk_id,
        FinalSubjectGrade.academic_year == current_year
    ).all()

    if not grades:
        return jsonify({'message': f'No final report found for student {zk_id} in {current_year}'}), 404

    # 2. تحديد النتيجة العامة والترتيب (نقوم بجلبها من أول سجل)
    general_result_db = grades[0].general_result if grades else 'غير محدد'
    overall_ranking_db = grades[0].overall_ranking if grades else 'غير محدد' # 🔑 جلب الترتيب من قاعدة البيانات
    
    # جلب اسم الصف ومنطق بناء قائمة الدرجات... 
    class_name = 'غير محدد'
    try:
        if 'Class' in globals() and hasattr(student, 'class_id') and student.class_id:
            student_class = Class.query.get(student.class_id)
            if student_class:
                class_name = student_class.name
    except Exception:
        pass
        
    overall_total = sum(grade.subject_total for grade in grades)
    
    final_grades_list = []
    for grade in grades:
        final_grades_list.append({
            'subject_name': grade.subject_name,
            'first_term_total': grade.first_acc_grade or 0.0, 
            'first_term_result_grade': grade.first_acc_result or 0.0, 
            'second_term_total': grade.second_acc_grade or 0.0, 
            'second_term_result_grade': grade.second_acc_result or 0.0, 
            'total_aggregate': grade.subject_total or 0.0,
        })
    
    # 3. بناء ملخص التقرير (FinalReportSummary)
    report_data = {
        'student_name': student.name,
        'class_name': class_name,
        'academic_year': current_year,
        'overall_total': overall_total or 0.0, 
        'overall_ranking': overall_ranking_db, # 🔑 إرسال الترتيب المدخل يدوياً
        'general_result': general_result_db, 
        'final_grades': final_grades_list,
    }

    return jsonify(report_data), 200
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++=

# ------------------------------------------
# 3.2 مسار حفظ وتحديث الدرجات النهائية (AJAX POST)
# ------------------------------------------
@app.route('/api/grades/final/save', methods=['POST'])
def save_final_subject_grade():
    data = request.json
    zk_id = data.get('student_zk_id')
    year = data.get('academic_year')
    
    # 🛑 تعديل: تحويل العام إلى عدد صحيح (int) 
    if year is not None:
        try:
            year = int(year)
        except ValueError:
            return jsonify({"success": False, "message": "العام الأكاديمي يجب أن يكون رقماً صحيحاً."}), 400
            
    subject = data.get('subject_name')

    # التحقق من الحقول الأساسية أولاً
    if not all([zk_id, year, subject]):
        return jsonify({"success": False, "message": "الرجاء توفير جميع الحقول المطلوبة (الطالب، العام، المادة)."}), 400
        
    # الدرجات المدخلة (يجب أن تكون أرقاماً، لذا نحولها إلى Float)
    try:
        first_acc_grade = float(data.get('first_acc_grade', 0))
        second_acc_grade = float(data.get('second_acc_grade', 0))
        first_acc_result = float(data.get('first_acc_result', 0))
        second_acc_result = float(data.get('second_acc_result', 0))
        
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "الرجاء إدخال أرقام صحيحة لجميع حقول الدرجات ونتائج المحصلات."}), 400
    
    # 🔑 الحساب الصحيح: المجموع الكلي هو مجموع الحقول الأربعة
    subject_total_grade = (first_acc_grade + second_acc_grade + 
                           first_acc_result + second_acc_result)
    # 🛑 تم حذف سطر الحساب الخاطئ الذي كان يعيد تعريف subject_total_grade 🛑

    # البحث عن سجل موجود
    grade = FinalSubjectGrade.query.filter_by(
        student_zk_id=zk_id, 
        academic_year=year, 
        subject_name=subject
    ).first()
    
    action = "تحديث" # القيمة الافتراضية للعملية

    if grade:
        # تحديث السجل الحالي
        grade.first_acc_grade = first_acc_grade
        grade.first_acc_result = first_acc_result
        grade.second_acc_grade = second_acc_grade
        grade.second_acc_result = second_acc_result
        grade.subject_total_grade = subject_total_grade
        
    else:
        # إنشاء سجل جديد
        grade = FinalSubjectGrade(
            student_zk_id=zk_id,
            academic_year=year,
            subject_name=subject,
            first_acc_grade=first_acc_grade,
            first_acc_result=first_acc_result,
            second_acc_grade=second_acc_grade,
            second_acc_result=second_acc_result,
            subject_total_grade=subject_total_grade
        )
        db.session.add(grade)
        action = "إدخال" # تغيير القيمة في حالة الإنشاء
        
    try:
        db.session.commit()
        
        # 💡 ملاحظة: يجب أن تضيف هنا استدعاء لدالة تقوم بتحديث المجموع الكلي للطالب (Overall Total) 
        # في جدول FinalStudentResult بعد حفظ كل مادة.
        
        return jsonify({
            "success": True, 
            "message": f"تم {action} درجة {subject} بنجاح.",
            # 🔑 إرسال المجموع الكلي باستخدام المفتاح 'total'
            "total": round(subject_total_grade, 2) 
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"خطأ في قاعدة البيانات: {str(e)}"}), 500
#===============================================================================================


@app.route('/login', methods=['GET', 'POST']) 
def login():
    if current_user.is_authenticated:
        # إذا كان المستخدم مسجلاً بالفعل، يتم إعادة توجيهه إلى لوحة الإدارة
        return redirect(url_for('admin_dashboard'))

    # 1. محاولة إيجاد أي مستخدم في قاعدة البيانات
    user = User.query.first()

    if not user:
        # 2. إذا لم يتم العثور على أي مستخدم، قم بإنشاء مستخدم افتراضي
        try:
            user = User(username='__auto_user__')
            db.session.add(user)
            db.session.commit()
            print("--- تم إنشاء مستخدم افتراضي جديد '__auto_user__' لغرض الدخول التلقائي. ---")
        except Exception as e:
            # إذا فشلت العملية لأسباب تتعلق بالـ DB (مثل عدم وجود جدول)
            flash(f'خطأ: فشل إعداد قاعدة البيانات للمستخدم التلقائي. {e}', 'error')
            return redirect(url_for('admin_dashboard')) # يمكنك تغيير التوجيه حسب الحاجة

    # 3. تسجيل الدخول التلقائي باستخدام Flask-Login
    login_user(user)
    flash(f'تم تسجيل الدخول التلقائي بنجاح كـ {user.username}.', 'success')
    
    # 4. إعادة التوجيه إلى الصفحة المطلوبة
    next_page = request.args.get('next')
    return redirect(next_page or url_for('admin_dashboard'))



@app.route('/login', methods=['POST'])
def login():
    # 1. قراءة بيانات JSON من التطبيق
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "❌ الرجاء إدخال اسم المستخدم وكلمة المرور."}), 400

    # البحث عن المستخدم
    user = User.query.filter_by(username=username).first()

    # 2. التحقق المباشر (نص عادي)
    if user and user.password == password:
        
        # 3. 🛑 السطر الناقص والأهم: تفعيل الجلسة للمستخدم
        login_user(user)

        # 4. تجميع بيانات الأبناء لإرسالها للتطبيق
        students_data = []
        for student in user.students:
            students_data.append({
                'student_id': student.id,
                'zk_id': student.zk_user_id,
                'name': student.name,
                'class_name': student.current_class.name if student.current_class else 'غير محدد'
            })

        # 5. النجاح: إرسال قائمة الأبناء مع رسالة نجاح (اختياري)
        # يمكنك إرسال البيانات مباشرة كما فعلت أنت
        return jsonify(students_data), 200
    
    else:
        # الفشل
        return jsonify({"message": "❌ اسم المستخدم أو كلمة المرور غير صحيحة."}), 401
# مسار تسجيل الخروج (يبقى كما هو)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج. سيتم تسجيل الدخول تلقائيًا عند محاولة الوصول لصفحة محمية.', 'info')
    # 💡 إعادة التوجيه إلى مسار الدخول التلقائي
    return redirect(url_for('login')) 



@app.route('/admin/reports/attendance_form')
@login_required # Assuming this route is protected
def admin_attendance_report_form():
    """
    يعرض النموذج الذي يحدد المعايير لتقرير الحضور.
    يمرر قائمة الطلاب والسنة الحالية إلى النموذج.
    """
    try:
        # Assuming you fetch all students here
        students = Student.query.all()
        
        # 💡 FIX: Calculate the current year in Python and pass it to the template
        current_year = datetime.now().year
        
        return render_template(
            'attendance_report_form.html', 
            students=students, 
            current_year=current_year # 💡 يتم تمرير السنة الحالية هنا
        )
    except Exception as e:
        # Log the error and handle it gracefully
        print(f"Error loading attendance form: {e}")
        flash('حدث خطأ أثناء تحميل نموذج تقرير الحضور.', 'danger')
        return redirect(url_for('admin_dashboard')) # Redirect to a safe page if loading fails

# ... (rest of app.py content)

@app.route('/admin/reports/attendance_view/<string:zk_id>/<int:year>', methods=['GET'])
def admin_attendance_report_view(zk_id, year):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not (start_date and end_date):
        return jsonify({"message": "الرجاء تحديد تاريخ البدء والانتهاء"}), 400

    student = Student.query.filter_by(zk_user_id=zk_id).first()
    if not student:
        return "الطالب غير موجود", 404

    attendance_records = Attendance.query.filter(
        Attendance.student_zk_id == zk_id,
        cast(Attendance.date, Date) >= start_date,
        cast(Attendance.date, Date) <= end_date
    ).order_by(Attendance.date).all()

    total_days = (datetime.strptime(end_date, '%Y-%m-%d').date() - datetime.strptime(start_date, '%Y-%m-%d').date()).days + 1
    present_count = sum(1 for r in attendance_records if r.status == 'present')
    absent_count = sum(1 for r in attendance_records if r.status == 'absent')
    late_count = sum(1 for r in attendance_records if r.status == 'late')

    report_data = {
        'student_name': student.name,
        'zk_id': zk_id,
        'class_name': student.current_class.name if student.current_class else 'غير محدد',
        'year': year,
        'start_date': start_date,
        'end_date': end_date,
        'records': attendance_records,
        'summary': {
            'total_days': total_days,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count
        }
    }

    return render_template('attendance_report_view.html', report=report_data)


# 🆕🆕🆕 مسار لوحة تحكم أولياء الأمور (الحل الجذري لمشكلة الشريط العلوي)
@app.route('/parent_dashboard', endpoint='parent_dashboard')
@login_required # شرط تسجيل الدخول
def parent_dashboard():
    # التحقق للتأكد من أن المستخدم المسجل هو ولي أمر
    if current_user.role != 'parent':
        flash('ليس لديك صلاحية للدخول كولي أمر.', 'danger')
        return redirect(url_for('login'))

    parent = current_user # الآن current_user هو كائن User المسجل دخوله
    students = parent.students.all()
    # تأكد من تعريف دالة get_current_year() لديك
    # current_year = get_current_year() 

    # استخدم get_current_year أو قيمة افتراضية حتى نحدد مكانها
    return render_template('parent_dashboard.html',
                            parent=parent,
                            students=students)
# ------------------------------------------
# 6.2 مسارات الإرسال والحفظ (POST/Export Routes)
# ------------------------------------------

@app.route('/api/admin/mid_term/export', methods=['POST'])
def export_mid_term_grade():
    data = request.get_json()

    zk_id = data.get('student_zk_id')
    year = data.get('academic_year')
    subject_name = data.get('subject_name')
    accumulated_grade = data.get('accumulated_grade', 0)
    end_term_grade = data.get('end_term_grade', 0)

    total_grade = accumulated_grade + end_term_grade
    result = calculate_mid_term_result(total_grade, subject_name)

    mid_term_grade = MidTermGrade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year,
        subject_name=subject_name
    ).first()

    if mid_term_grade:
        mid_term_grade.accumulated_grade = accumulated_grade
        mid_term_grade.end_term_grade = end_term_grade
        mid_term_grade.term_total_grade = total_grade
        mid_term_grade.result = result
        message = "تم تحديث الدرجات النصفية بنجاح."
    else:
        new_grade = MidTermGrade(
            student_zk_id=zk_id,
            academic_year=year,
            subject_name=subject_name,
            accumulated_grade=accumulated_grade,
            end_term_grade=end_term_grade,
            term_total_grade=total_grade,
            result=result
        )
        db.session.add(new_grade)
        message = "تم إدخال الدرجات النصفية بنجاح."

    try:
        db.session.commit()
        return jsonify({"message": message, "total_grade": total_grade}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"خطأ في قاعدة البيانات: {str(e)}"}), 500

@app.route('/api/admin/final_grade/export', methods=['POST'])
def export_final_grade():
    data = request.get_json()

    zk_id = data.get('student_zk_id')
    year = data.get('academic_year')
    overall_total = int(data.get('total_aggregate', 0))
    general_result = 'ناجح' if overall_total >= 600 else 'راسب'

    final_grade = FinalGrade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year,
    ).first()

    if final_grade:
        final_grade.overall_total = overall_total
        final_grade.general_result = general_result
        message = "تم تحديث النتيجة النهائية بنجاح."
    else:
        new_grade = FinalGrade(
            student_zk_id=zk_id,
            academic_year=year,
            overall_total=overall_total,
            general_result=general_result,
            overall_ranking=0
        )
        db.session.add(new_grade)
        message = "تم إدخال النتيجة النهائية بنجاح."

    try:
        db.session.commit()
        return jsonify({"message": message, "total_aggregate": overall_total}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"خطأ في قاعدة البيانات: {str(e)}"}), 500

# ------------------------------------------
# 6.3 مسارات عرض التقارير (Search/View Routes)
# ------------------------------------------
#==================================================================================================
@app.route('/api/grades/save/<string:zk_id>/<string:month_name>/<int:year>', methods=['POST'])
def save_monthly_grade(zk_id, month_name, year):
    # 1. استلام البيانات المرسلة بصيغة JSON
    data = request.get_json()
    if not data:
        return jsonify({"message": "فشل: لم يتم إرسال بيانات الدرجات."}), 400

    subject_name = data.get('subject_name')
    if not subject_name:
        return jsonify({"message": "فشل: المادة الدراسية غير محددة."}), 400
        
    # 2. استخراج الدرجات
    try:
        homework_grade = int(data.get('homework_grade', 0))
        oral_grade = int(data.get('oral_grade', 0))
        attendance_grade = int(data.get('attendance_grade', 0))
        written_grade = int(data.get('written_grade', 0))
        app = int(data.get('app', 0))
        supplies = int(data.get('supplies', 0))
    except ValueError:
        return jsonify({"message": "فشل: يجب أن تكون قيم الدرجات أرقاماً صحيحة."}), 400

    # 3. حساب المجموع الكلي
    total_grade = homework_grade + oral_grade + attendance_grade + written_grade + app

    # 4. البحث عن سجل موجود (للتحديث) - 🛑 تم تغيير year=year إلى academic_year=year
    grade_item = Grade.query.filter_by(
        student_zk_id=zk_id,
        year=year, # 🛑 استخدمنا academic_year الذي هو اسم العمود الصحيح
        month_name=month_name,
        subject_name=subject_name
    ).first()
    
    message = ""

    if grade_item:
        # تحديث السجل الموجود
        grade_item.homework_grade = homework_grade
        grade_item.oral_grade = oral_grade
        grade_item.attendance_grade = attendance_grade
        grade_item.written_grade = written_grade
        grade_item.app = app
        grade_item.total_grade = total_grade # 🆕 تحديث حقل المجموع الكلي
        grade_item.supplies = supplies
        # (حقل result يمكن تحديثه لاحقاً أو تركه للقيمة الافتراضية 'NA')
        message = "تم تحديث درجات المادة بنجاح."
    else:
        # إنشاء سجل جديد
        try:
            new_grade = Grade(
                student_zk_id=zk_id,
                year=year, # 🛑 استخدمنا academic_year هنا أيضاً
                month_name=month_name,
                subject_name=subject_name,
                homework_grade=homework_grade,
                oral_grade=oral_grade,
                attendance_grade=attendance_grade,
                written_grade=written_grade,
                supplies=supplies,
                app=app,
                total_grade=total_grade # 🆕 إضافة المجموع الكلي أثناء الإنشاء
            )
            db.session.add(new_grade)
            message = "تم حفظ الدرجات الجديدة بنجاح."
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"خطأ في إنشاء سجل جديد (تحقق من المفاتيح الخارجية): {str(e)}"}), 500

    # 5. حفظ التغييرات في قاعدة البيانات
    try:
        db.session.commit()
        return jsonify({
            "message": message,
            "total_grade": total_grade,
            "zk_id": zk_id,
            "month_name": month_name
        }), 200 # تم الحفظ بنجاح
    except Exception as e:
        db.session.rollback()
        # هنا قد تحتاج لطباعة الخطأ كاملاً لمعرفة سبب فشل الـ commit
        print(f"Database Commit Failed: {str(e)}")
        return jsonify({"message": f"فشل في حفظ التغييرات إلى قاعدة البيانات: {str(e)}"}), 500
    #=============================================================================================================


@app.route('/grades/entry')
def grades_entry_home():
    """عرض صفحة تحتوي على خيارات إدخال الدرجات الثلاثة."""
    # سيتم عرض القالب التالي
    return render_template('grades_entry_home.html', title='إدخال الدرجات')



@app.route('/admin/grade/save', methods=['POST'])
def admin_grade_save():
    """
    معالجة بيانات نموذج إدخال الدرجات الفردي وحفظها أو تحديثها.
    🔑 تم تعديلها لتتوافق مع الأعمدة الجديدة: student_zk_id, month_name, final_total_grade
    """
    try:
        # 1. جمع البيانات من النموذج
        zk_user_id = request.form.get('zk_id', '').strip()
        subject_name = request.form.get('subject_name', '').strip()
        month_name = request.form.get('month_name', '').strip() # نستخدم الاسم النصي مباشرة
        year_str = request.form.get('year', '').strip()
        
        # التأكد من تحويل الدرجات إلى أعداد صحيحة
        homework_grade = int(request.form.get('homework_grade', 0))
        oral_grade = int(request.form.get('oral_grade', 0))
        attendance_grade = int(request.form.get('attendance_grade', 0))
        written_grade = int(request.form.get('written_grade', 0))
        app = int(request.form.get('app', 0))
        supplies = int(request.form.get('supplies', 0))
        
        # 🔑 استخدام final_total_grade
        final_total_grade = int(request.form.get('grade_value', 0)) # المجموع الكلي القادم من النموذج
        
        # يُمكنك إضافة منطق لحساب النتيجة (Pass/Fail) هنا إذا لزم الأمر
        result = "ناجح" if final_total_grade >= 50 else "راسب" # مثال بسيط

        # 2. التحقق من البيانات الأساسية
        if not all([zk_user_id, subject_name, month_name, year_str]):
            flash('الرجاء تعبئة جميع الحقول المطلوبة.', 'danger')
            return redirect(url_for('admin_grade_entry_form'))

        year = int(year_str)

        # 3. البحث عن الطالب
        student = db.session.query(Student).filter_by(zk_user_id=zk_user_id).first()
        if not student:
            flash(f'لم يتم العثور على طالب بالرقم التعريفي: {zk_user_id}.', 'danger')
            return redirect(url_for('admin_grade_entry_form'))
        
        # 4. البحث عن الدرجة الموجودة أو إنشاء درجة جديدة
        # 🔑 الاستعلام الآن يستخدم student_zk_id, year, month_name, subject_name
        grade = db.session.query(MonthlyGrade).filter_by(
            student_zk_id=zk_user_id,
            subject_name=subject_name,
            month_name=month_name,
            year=year
        ).first()

        if grade:
            # تحديث الدرجة الموجودة
            grade.final_total_grade = final_total_grade
            grade.homework_grade = homework_grade
            grade.oral_grade = oral_grade
            grade.attendance_grade = attendance_grade
            grade.written_grade = written_grade
            grade.app = app
            grade.supplies = supplies
            grade.result = result # تحديث النتيجة
            message = 'تم تحديث الدرجة بنجاح.'
        else:
            # إنشاء درجة جديدة
            new_grade = MonthlyGrade(
                student_zk_id=zk_user_id,
                subject_name=subject_name,
                month_name=month_name,
                year=year,
                final_total_grade=final_total_grade,
                homework_grade=homework_grade,
                oral_grade=oral_grade,
                attendance_grade=attendance_grade,
                written_grade=written_grade,
                app=app,
                supplies=supplies,
                result=result
            )
            db.session.add(new_grade)
            message = 'تم إضافة الدرجة بنجاح.'

        db.session.commit()
        flash(message, 'success')
        
    except ValueError:
        db.session.rollback()
        flash('حدث خطأ في تحويل الدرجات إلى أرقام صحيحة. الرجاء إدخال أرقام فقط.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving grade: {e}")
        # 🔑 رسالة الخطأ العامة
        flash(f'❌ حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
        
    return redirect(url_for('admin_grade_entry_form'))

TIMEZONE = 'Asia/Riyadh' 
ARABIC_MONTHS = [
    (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'), 
    (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'), 
    (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
]

def get_academic_years():
    """يحسب قائمة السنوات الأكاديمية المحتملة (الحالية والسابقة)."""
    current_year = datetime.now(pytz.timezone(TIMEZONE)).year
    # يعرض السنوات من 5 سنوات سابقة إلى سنتين قادمتين
    return [y for y in range(current_year - 5, current_year + 2)]
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


@app.route('/admin/search/monthly', methods=['GET', 'POST'])
def admin_search_monthly_grades():
    """
    نموذج البحث عن الدرجات الشهرية للطالب.
    """
    
    # 1. جلب الخيارات الأساسية للنموذج (تتم في بداية الدالة لضمان توفرها في POST و GET)
    students = db.session.query(Student).order_by(Student.name).all()
    months = ARABIC_MONTHS # قائمة الأشهر
    years = get_academic_years() # قائمة السنوات الأكاديمية المتاحة (مثلاً: [2022, 2023, 2024])
    
    # تحديد العام المحدد مسبقاً: نختار أحدث عام (أو عام محدد عند إعادة التحميل بعد POST فاشل)
    # نستخدم العام الحالي كقيمة افتراضية في حالة عدم وجود سنوات متاحة من الدالة
    current_year = datetime.now().year
    selected_year = years[-1] if years else current_year

    if request.method == 'POST':
        # 2. استلام البيانات من النموذج باستخدام أسماء الحقول الجديدة في HTML: 'zk_id', 'month', 'year'
        student_zk_id = request.form.get('zk_id')  # كان في السابق 'student_zk_id'
        month_id = request.form.get('month')  # كان في السابق 'month_id'
        academic_year = request.form.get('year') # كان في السابق 'academic_year'
        
        
        if student_zk_id and month_id and academic_year:
            try:
                # 3. إعادة توجيه باستخدام أسماء المعاملات المتوقعة من دالة العرض (admin_view_monthly_grades)
                return redirect(url_for('admin_view_monthly_grades', 
                                         student_zk_id=student_zk_id, 
                                         month_id=int(month_id), 
                                         academic_year=int(academic_year)))
            except Exception as e:
                current_app.logger.error(f"Error building URL for view page: {e}. Using static path as fallback.")
                return redirect(f'/admin/view/monthly/{student_zk_id}/{month_id}/{academic_year}')
        
        else:
            flash("الرجاء اختيار الطالب والشهر والعام الأكاديمي بشكل صحيح.", "danger")
            # في حالة فشل التحقق، نعيد عرض النموذج مع الاحتفاظ بـ academic_years
            return render_template('search_monthly_grades.html', 
                                   students=students, 
                                   # يجب استخدام 'academic_years' ليتطابق مع ما تم تحديده في قالب Jinja
                                   academic_years=years, 
                                   selected_year=selected_year)

    # 4. عرض نموذج البحث (GET request)
    return render_template('search_monthly_grades.html', 
                           students=students, 
                           # يجب استخدام 'academic_years' ليتطابق مع ما تم تحديده في قالب Jinja
                           academic_years=years, 
                           selected_year=selected_year)


    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


from sqlalchemy import func # تأكد من استيراد func من sqlalchemy

@app.route('/admin/view/monthly/<string:student_zk_id>/<int:month_id>/<int:academic_year>', methods=['GET', 'POST'])
def admin_view_monthly_grades(student_zk_id, month_id, academic_year):
    # 1. جلب اسم الشهر بالعربية
    month_name = next((name for id, name in ARABIC_MONTHS if id == month_id), None)

    # 2. جلب بيانات الطالب - جربنا فلترة الحقل النصي والرقمي لضمان المطابقة
    # ملاحظة: تأكد أن اسم الحقل في موديل Student هو 'zk_user_id'
    student = db.session.query(Student).filter(
        (Student.zk_user_id == student_zk_id) | (Student.zk_user_id == str(student_zk_id))
    ).first()

    if request.method == 'POST':
        grade_ids = request.form.getlist('grade_id')
        updated_count = 0
        try:
            for g_id in grade_ids:
                grade_record = db.session.query(MonthlyGrade).get(int(g_id))
                if grade_record:
                    def clean_grade(val):
                        try:
                            return int(float(val)) if val and str(val).strip() != "" else 0
                        except: return 0

                    grade_record.homework_grade = clean_grade(request.form.get(f'homework_{g_id}'))
                    grade_record.oral_grade = clean_grade(request.form.get(f'oral_{g_id}'))
                    grade_record.attendance_grade = clean_grade(request.form.get(f'attendance_{g_id}'))
                    grade_record.written_grade = clean_grade(request.form.get(f'written_{g_id}'))
                    grade_record.app = clean_grade(request.form.get(f'app_{g_id}'))
                    grade_record.supplies = clean_grade(request.form.get(f'supplies_{g_id}'))
                    
                    grade_record.final_total_grade = (grade_record.homework_grade + 
                                                     grade_record.oral_grade + 
                                                     grade_record.attendance_grade + 
                                                     grade_record.written_grade+grade_record.app)
                    
                    grade_record.result = "ناجح" if grade_record.final_total_grade >= 50 else "راسب"
                    updated_count += 1
            
            db.session.commit()
            flash(f'✅ تم تحديث {updated_count} سجل بنجاح', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ خطأ في الحفظ: {str(e)}', 'danger')
            
        return redirect(url_for('admin_view_monthly_grades', 
                               student_zk_id=student_zk_id, 
                               month_id=month_id, 
                               academic_year=academic_year))

    # 3. جلب الدرجات
    grades = db.session.query(MonthlyGrade).filter(
        MonthlyGrade.student_zk_id == student_zk_id,
        MonthlyGrade.year == academic_year,
        MonthlyGrade.month_name == month_name
    ).all()

    # نرسل الطالب والدرجات للقالب
    return render_template('view_monthly_grades.html', 
                           student=student, 
                           grades=grades, 
                           month_name=month_name, 
                           academic_year=academic_year,
                           debug_id=student_zk_id) # أضفنا المعرف للتصحيح


#//////////////////////////////////////////////////////////////////////
# حفظ البيانات الشهريه للوحه التحكم
@app.route('/admin/save_grades', methods=['POST'])
def save_grades():
    # اطبع كل البيانات القادمة من المتصفح في الـ Terminal
    print("--- Incoming Data ---")
    print(request.form) 
    
    grade_ids = request.form.getlist('grade_id')
    print(f"IDs received: {grade_ids}")

    if not grade_ids:
        return "No IDs received from form", 400

    try:
        for g_id in grade_ids:
            grade_record = MonthlyGrade.query.get(g_id)
            if grade_record:
                # جلب القيم المباشرة
                hw = request.form.get(f'homework_{g_id}')
                print(f"Updating ID {g_id} with homework: {hw}")
                
                if hw is not None:
                    grade_record.homework_grade = int(hw)
            else:
                print(f"Record with ID {g_id} not found in database")

        db.session.commit()
        return "Saved successfully", 200
    except Exception as e:
        db.session.rollback()
        print(f"Database Error: {e}")
        return str(e), 500




@app.route('/admin/grade/export/<string:zk_id>/<string:month>/<string:year>', methods=['GET'], endpoint='export_monthly_grades_to_excel')
def export_monthly_grades_to_excel(zk_id, month, year):
    """تصدير الدرجات الشهرية إلى ملف Excel/CSV بناءً على الطالب، الشهر، والسنة."""
    try:
        # جلب الدرجات
        grades = MonthlyGrade.query.filter(
            MonthlyGrade.zk_user_id == zk_id,
            MonthlyGrade.month_name == month,
            MonthlyGrade.academic_year == year 
        ).all()

        if not grades:
            flash("لا توجد درجات لتصديرها بالمعايير المحددة.", 'danger')
            return redirect(url_for('admin_grade_entry_form'))

        # جلب اسم الطالب (لأغراض التسمية)
        student = Student.query.filter_by(zk_user_id=zk_id).first()
        student_name = student.name if student else zk_id

        # تحويل البيانات إلى DataFrame
        data = [{
            'اسم الطالب': student_name,
            'المادة': grade.subject_name,
            'الشهر': grade.month_name,
            'السنة': grade.academic_year,
            'الواجبات': grade.homework_grade,
            'الشفهي': grade.oral_grade,
            'الحضور': grade.attendance_grade,
            'التحريري': grade.written_grade,
            'التطبيق': grade.app,
            'المجموع': grade.total_grade,
            'المحصلة': grade.supplies,
            'تاريخ الإدخال': grade.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for grade in grades]
        
        df = pd.DataFrame(data)

        # حفظ في ذاكرة مؤقتة كملف CSV
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        filename = f'{student_name}_{month}_{year}.csv'

        return send_file(output,
                            mimetype='text/csv',
                            as_attachment=True,
                            download_name=filename)
    
    except Exception as e:
        # 🛑 تم التعديل: التأكد من تصحيح اسم نقطة النهاية عند الفشل
        flash(f"فشل التصدير: {e}", 'danger')
        return redirect(url_for('admin_grade_entry_form'))


# ------------------------------------------
# ملاحظة حول خطأ التصدير:
# إذا كان لديك أي رابط في قالب HTML يشير إلى التصدير، تأكد من أن شكله هو:
# <a href="{{ url_for('export_monthly_grades_to_excel', zk_id=..., month=..., year=...) }}">تصدير</a>
# وتأكد من أن اسم نقطة النهاية هو 'export_monthly_grades_to_excel' وليس 'export_monthly_grades_excel'.
# ------------------------------------------
#============================================================================================================================

@app.route('/admin/export/monthly/<string:zk_id>/<string:month>/<int:year>', methods=['GET'])
def export_monthly_grades_file(zk_id, month, year):
    grades = Grade.query.filter_by(
        student_zk_id=zk_id,
        academic_year=year,
        month_name=month
    ).all()

    if not grades:
        return "لا توجد بيانات درجات شهرية لهذا الطالب والشهر.", 404

    student = Student.query.filter_by(zk_user_id=zk_id).first()
    student_name = student.name if student else 'طالب غير معروف'

    data = [{
        'المادة': g.subject_name,
        'واجب': g.homework_grade,
        'شفوي': g.oral_grade,
        'حضور': g.attendance_grade,
        'تحريري': g.written_grade,
        ' التطبيق': g.app,
        'المجموع الشهري': g.total_grade,
        ' المحصلة': g.supplies,

        'النتيجة': g.result
    } for g in grades]

    monthly_total = sum(g.total_grade for g in grades)
    data.append({
        'المادة': 'المجموع الكلي',
        'واجب': '', 'شفوي': '', 'حضور': '', 'تحريري': '','التطبيق': '',
        'المجموع الشهري': monthly_total,'المحصلة': '',
        'النتيجة': ''
    })

    df = pd.DataFrame(data)

    output = BytesIO()
    df.to_csv(output, encoding='utf-8-sig', index=False)
    output.seek(0)

    filename = f'تقرير_الدرجات_الشهرية_{student_name}_{month}_{year}.csv'

    return send_file(output,
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=filename)

# ------------------------------------------
# 6.4 مسارات إدارة الصفوف والترحيل (Class Routes)
# ------------------------------------------

@app.route('/admin/classes')
def admin_classes_list():
    classes = db.session.query(Class).order_by(Class.id).all()
    return render_template('classes_list.html', classes=classes)

@app.route('/admin/transfer_students', methods=['POST'])
def admin_transfer_students():
    class_id = request.form.get('class_id')
    current_class = Class.query.get(class_id)

    if not current_class or not current_class.next_class:
        return "الصف غير موجود أو لم يحدد له صف ترحيل.", 400

    next_class = current_class.next_class

    students_to_transfer = current_class.students.all()
    count = 0
    for student in students_to_transfer:
        student.class_id = next_class.id
        count += 1

    try:
        db.session.commit()
        return f"تم ترحيل {count} طالب بنجاح من صف {current_class.name} إلى صف {next_class.name}."
    except Exception as e:
        db.session.rollback()
        return f"حدث خطأ أثناء الترحيل: {str(e)}", 500


if __name__ == '__main__':
    # يمكن تفعيل دالة create_db_tables() لإنشاء الجداول في حال لم تكن موجودة
    # create_db_tables()
    app.run(debug=True, port=4370)
    
