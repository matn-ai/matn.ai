from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, FieldList, FormField, TextAreaField, HiddenField, RadioField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo, URL
from flask import flash
from ..const import ARTICLE_BLOG_POST, ARTICLE_GENERAL, ARTICLE_PRO


class URLFieldForm(FlaskForm):
    url = StringField('لینک‌ورودی', validators=[URL(message='آدرس نامعتبر')])


class GenerateArticleBlog(FlaskForm):
    user_topic = TextAreaField('عنوان', validators=[DataRequired(), Length(1, 500)])
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    body = TextAreaField('محتوا')
    article_length = RadioField('Article Length', choices=[('short', 'پست کوتاه'), ('long', 'پست بلند')], default='short')
    content_type = HiddenField(default=ARTICLE_BLOG_POST)
    submit = SubmitField('تولید مقاله')
    




class GenerateArticlePro(FlaskForm):
    user_topic = TextAreaField('عنوان', validators=[DataRequired(), Length(1, 500)])
    urls = FieldList(FormField(URLFieldForm), min_entries=1, max_entries=10)
    main_tag = StringField('کلمه کلیدی اصلی', validators=[DataRequired()])
    tags = StringField('کلمات کلیدی')
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    body = TextAreaField('محتوا')
    content_type = HiddenField(default=ARTICLE_PRO)
    submit = SubmitField('تولید مقاله')

    point_ofview = SelectField('زاویه دید را انتخاب کنید', choices=[
        ('first_person_singular', 'اول شخص مفرد (من)'),
        ('first_person_plural', 'اول شخص جمع (ما)'),
        ('second_person', 'دوم شخص مفرد یا جمع (تو/شما)'),
        ('third_person_singular', 'سوم شخص مفرد (او)'),
        ('third_person_plural', 'سوم شخص جمع (آنها)'),
        ('neutral_objective', 'بی‌ طرف و عینی'),
        ('personal_experiential', 'شخصی و تجربی'),
        ('reportive_news', 'گزارشی و خبری'),
        ('analytical_interpretive', 'تحلیلی و تفسیرکننده'),
        ('persuasive_convincing', 'ترغیبی و اقناعی'),
        ('narrative_storytelling', 'روایتگر و داستانی'),
        ('descriptive_detailed', 'توصیفی و جزئی‌نگر'),
        ('factual_evidence', 'مستند و حقایق‌محور'),
        ('critical_evaluative', 'نقد و ارزیابی‌کننده'),
        ('educational_guiding', 'آموزشی و راهنما')
    ])

    target_audience = SelectField('گروه هدف را انتخاب کنید', choices=[
        ('general_public', 'عموم مردم'),
        ('tech_enthusiasts', 'افراد علاقه‌مند به فناوری'),
        ('learners_development', 'علاقه‌مندان به یادگیری و توسعه فردی'),
        ('news_information', 'علاقه‌مندان به اخبار و اطلاعات'),
        ('social_media_users', 'افراد فعال در شبکه‌های اجتماعی'),
        ('researchers_academics', 'پژوهشگران و محققان'),
        ('families_parents', 'خانواده‌ها و والدین'),
        ('leisure_entertainment', 'علاقه‌مندان به تفریح و سرگرمی'),
        ('travelers_tourists', 'مسافران و گردشگران'),
        ('employees_workers', 'شاغلین و کارکنان بخش‌های مختلف'),
        ('health_wellness', 'علاقه‌مندان به بهبود سلامتی و تندرستی'),
        ('fashion_beauty', 'علاقه‌مندان به مد و زیبایی'),
        ('finance_investment', 'علاقه‌مندان به امور مالی و سرمایه‌گذاری'),
        ('food_cooking', 'علاقه‌مندان به غذا و آشپزی'),
        ('environment_sustainability', 'دوستداران محیط زیست و پایداری'),
        ('managers', 'مدیران شرکت‌ها و کسب‌وکارها'),
        ('entrepreneurs_startups', 'کارآفرینان و استارتاپ‌ها'),
        ('seo_digital_marketers', 'متخصصان سئو و بازاریابی دیجیتال'),
        ('writers_content_creators', 'نویسندگان و تولیدکنندگان محتوا'),
        ('students_professors', 'دانشجویان و اساتید دانشگاه'),
        ('website_owners_bloggers', 'صاحبان وب‌سایت‌ها و بلاگرها'),
        ('business_marketing_consultants', 'مشاوران کسب‌وکار و بازاریابی'),
        ('online_sellers_ecommerce', 'فروشندگان آنلاین و فروشگاه‌های الکترونیکی'),
        ('journalists_reporters', 'روزنامه‌نگاران و خبرنگاران'),
        ('tech_software_companies', 'شرکت‌های فن‌آوری و نرم‌افزار'),
        ('educational_coaches_consultants', 'مربیان و مشاوران آموزشی'),
        ('social_media_influencers', 'فعالان شبکه‌های اجتماعی'),
        ('advertising_pr_managers', 'مدیران تبلیغات و روابط عمومی'),
        ('web_designers_developers', 'طراحان و توسعه‌دهندگان وب'),
        ('various_industries', 'صنایع مختلف (مثل مد، سلامت، مالی، و غیره)')
    ])

    article_length = SelectField('طول مقاله را انتخاب کنید', choices=[
        ('normal', 'معمولی (تا ۳۵۰۰ کلمه)'),
        ('short', 'کوتاه (زیر ۲۵۰۰ کلمه)'),
        ('professional', 'حرفه‌ای (+۵۰۰۰ کلمه)'),
        ('specialized', 'تخصصی (+۷۵۰۰ کلمه)'),
        ('booklet', 'کتابچه (+۱۰۰۰ کلمه)')
    ], default='normal')

    voice_tune = SelectField('لحن نوشته را انتخاب کنید', choices=[
        ('official_pro', 'رسمی و حرفه‌ای'),
        ('friendly_intimate', 'دوستانه و صمیمی'),
        ('educational_guiding', 'آموزشی و راهنما'),
        ('news_press', 'خبری و مطبوعاتی'),
        ('analytical_research', 'تحلیلی و پژوهشی'),
        ('conversational_informal', 'محاوره‌ای و غیر رسمی'),
        ('entertaining_creative', 'سرگرم‌کننده و خلاقانه'),
        ('technical_expert', 'فنی و متخصصانه'),
        ('advertorial_marketing', 'تبلیغاتی و بازاریابی'),
        ('inspirational_motivational', 'الهام‌بخش و انگیزشی'),
        ('leisure_enjoyable', 'تفریحی و لذت‌بخش'),
        ('serious_heavy', 'جدی و سنگین'),
        ('humorous_witty', 'طنز و شوخ‌طبعی'),
        ('simple_understandable', 'ساده و قابل‌فهم'),
        ('respectful_courteous', 'محترمانه و مودبانه')
    ])

    def __init__(self, *args, **kwargs):
        super(GenerateArticlePro, self).__init__(*args, **kwargs)
        if not self.urls.entries:
            self.urls.append_entry()
