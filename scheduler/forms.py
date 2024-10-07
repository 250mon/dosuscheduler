from datetime import date, datetime, time, timedelta

from flask_wtf import FlaskForm
from flask_wtf.recaptcha import validators
from wtforms import (
    DateField,
    EmailField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    TelField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
)

from scheduler import db
from scheduler.models import User


class ConfigForm(FlaskForm):
    name = StringField(
        "이 름", validators=[DataRequired("이름은 필수 입력 항목입니다.")]
    )
    is_default = RadioField(
        "현재셋팅",
        choices=[("yes", "Yes"), ("no", "No")],
        default="yes",
        validators=[DataRequired("Check if this is current settings.")],
    )
    start_date = DateField(
        "시작날짜",
        default=date.today().replace(day=1),
        validators=[DataRequired("시작날짜는 필수 입력 항목입니다")],
    )
    end_date = DateField(
        "종료날짜",
        default=date(9999, 12, 31),
        validators=[DataRequired("종료날짜는 필수 입력 항목입니다")],
    )
    wd_start_hour = TimeField(
        "평일시작시간",
        default=time(hour=9),
        render_kw={"step": 1800},
        validators=[DataRequired("평일시작시간은 필수 입력 항목입니다")],
    )
    wd_end_hour = TimeField(
        "평일종료시간",
        default=time(hour=21),
        render_kw={"step": "1800"},
        validators=[DataRequired("평일종료시간은 필수 입력 항목입니다")],
    )
    wd_lunch_start_hour = TimeField(
        "평일점심시작시간",
        default=time(hour=13),
        render_kw={"step": "1800"},
        validators=[DataRequired("평일점심시작시간은 필수 입력 항목입니다")],
    )
    wd_lunch_end_hour = TimeField(
        "평일점심종료시간",
        default=time(hour=14),
        render_kw={"step": "1800"},
        validators=[DataRequired("평일점심종료시간은 필수 입력 항목입니다")],
    )
    wd_overtime_hour = TimeField(
        "평일오버타임시작시간",
        default=time(hour=18),
        render_kw={"step": "1800"},
        validators=[DataRequired("평일오버타임시작시간은 필수 입력 항목입니다")],
    )
    sd_start_hour = TimeField(
        "토요일시작시간",
        default=time(hour=9),
        render_kw={"step": "1800"},
        validators=[DataRequired("토요일시작시간은 필수 입력 항목입니다")],
    )
    sd_end_hour = TimeField(
        "토요일종료시간",
        default=time(hour=15),
        render_kw={"step": "1800"},
        validators=[DataRequired("토요일종료시간은 필수 입력 항목입니다")],
    )
    sd_overtime_hour = TimeField(
        "토요일오버타임시작시간",
        default=time(hour=13),
        render_kw={"step": "1800"},
        validators=[DataRequired("토요일오버타임시작시간은 필수 입력 항목입니다")],
    )
    duration = SelectField(
        "슬롯시간",
        choices=[
            (10, "10분"),
            (20, "20분"),
            (30, "30분"),
        ],
        default=10,
        validators=[DataRequired("슬롯시간은 필수 입력 항목입니다.")],
    )


class WorkerForm(FlaskForm):
    user_id = IntegerField(
        "유저번호",
        default=1,
        validators=[DataRequired("유저번호는 필수 입력 항목입니다.")],
    )
    name = StringField(
        "이 름", validators=[DataRequired("이름은 필수 입력 항목입니다.")]
    )
    room = SelectField(
        "치료실",
        choices=[("1", "치료실1"), ("2", "치료실2")],
        default="1",
        validators=[DataRequired("치료실은 필수 입력 항목입니다.")],
    )
    available = RadioField(
        "활성상태",
        choices=[("yes", "활성"), ("no", "비활성")],
        default="yes",
        validators=[DataRequired("Check if it is available.")],
    )


class PatientForm(FlaskForm):
    mrn = IntegerField(
        "환자번호",
        validators=[
            InputRequired("환자번호는 필수 입력 항목입니다."),
            NumberRange(min=0, message="Not a negative integer"),
        ],
    )
    name = StringField(
        "이 름", validators=[DataRequired("이름은 필수 입력 항목입니다.")]
    )
    sex = RadioField(
        "성 별",
        choices=[("male", "남"), ("female", "여")],
        default="male",
        validators=[DataRequired("Check gender.")],
    )
    birthday = DateField(
        "생년월일", validators=[DataRequired("생년월일은 필수 입력 항목입니다.")]
    )
    tel = TelField("전화번호")
    note = TextAreaField("메 모")


class DosutypeForm(FlaskForm):
    name = StringField(
        "이 름", validators=[DataRequired("이름은 필수 입력 항목입니다.")]
    )
    order_code = StringField(
        "처방코드", validators=[DataRequired("처방코드는 필수 입력 항목입니다.")]
    )
    slot_quantity = SelectField(
        "타임단위갯수",
        choices=[
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4", "4"),
            ("5", "5"),
            ("6", "6"),
            ("7", "7"),
            ("8", "8"),
            ("100", "100"),
        ],
        validators=[DataRequired("타임슬롯수는 필수 입력 항목입니다.")],
    )
    price = IntegerField(
        "가 격",
        validators=[
            InputRequired("가격은 필수 입력 항목입니다."),
            NumberRange(min=0, message="Not a negative integer"),
        ],
    )
    available = StringField(
        "활성상태", validators=[DataRequired("Check if it is available.")]
    )


class DosusessForm(FlaskForm):
    dosusess_date = DateField(
        "날 짜", validators=[DataRequired("날짜는 필수 입력 항목입니다")]
    )
    slot = IntegerField(
        "타임슬롯번호", validators=[DataRequired("타임슬롯번호는 필수 입력 항목입니다")]
    )
    status = StringField(
        "상 태", validators=[DataRequired("상태는 필수 입력 항목입니다.")]
    )


class UserForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired("Username required"), Length(min=3, max=25)],
    )
    password1 = PasswordField(
        "Password",
        validators=[
            DataRequired("Password required"),
            EqualTo("password2", "not matched passwords"),
        ],
    )
    password2 = PasswordField(
        "Password to Confirm", validators=[DataRequired("Confirm required")]
    )
    email = EmailField("Email", validators=[Optional(), Email()])


class UserModifyForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired("Username required"), Length(min=3, max=25)],
    )
    password1 = PasswordField(
        "Password",
    )
    email = EmailField("Email", validators=[Optional(), Email()])
    privilege = SelectField(
        "Privilege",
        choices=[
            (5, "Admin"),
            (1, "User"),
        ],
        default=1,
        validators=[DataRequired("Privilege is required.")],
    )
    available = RadioField(
        "Availability",
        choices=[("yes", "활성"), ("no", "비활성")],
        default="yes",
        validators=[DataRequired("Check if it is available.")],
    )


class UserLoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired("Username required"), Length(min=3, max=25)],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired("Password required"),
        ],
    )


class PatientStatsForm(FlaskForm):
    mrn = IntegerField(
        "환자번호", validators=[DataRequired("환자번호는 필수 입력 항목입니다.")]
    )
    start_date = DateField(
        "조회시작일",
        render_kw={"max": date.today().strftime("%Y-%m-%d")},
        default=date.today().replace(month=date.today().month - 3),
        validators=[DataRequired("조회시작일은 필수 입력 항목입니다.")],
    )
    end_date = DateField(
        "조회종료일",
        render_kw={"max": date.today().strftime("%Y-%m-%d")},
        default=date.today().replace(day=date.today().day - 1),
        validators=[DataRequired("조회종료일은 필수 입력 항목입니다.")],
    )


class WorkerStatsForm(FlaskForm):
    id = IntegerField(
        "치료사번호", validators=[DataRequired("치료사번호는 필수 입력 항목입니다.")]
    )
    start_date = DateField(
        "조회시작일",
        render_kw={"max": date.today().strftime("%Y-%m-%d")},
        default=date.today().replace(day=1),
        validators=[DataRequired("조회시작일은 필수 입력 항목입니다.")],
    )
    end_date = DateField(
        "조회종료일",
        render_kw={"max": date.today().strftime("%Y-%m-%d")},
        default=date.today().replace(day=date.today().day - 1),
        validators=[DataRequired("조회종료일은 필수 입력 항목입니다.")],
    )
