# **📚 Library Management GUI Project | پروژه مدیریت کتابخانه گرافیکی**

**A university project in which a library management system is designed using PyQT5 and has user and admin parts.**

## Known Issues / 已知问题

- Importing `Code.Database` emits a `DeprecationWarning`. This is expected in the A1–A3 transition: SQLite access now lives in `repository/connection.py`, and user CRUD in `repository/user_repository.py`, but book/loan helpers still go through `Database.py`. The warning will go away when that module is retired. Search `# REFACTOR-TRANSITION` to find compatibility shims.
- `BookRepository.list_all(users_by_id)` still hydrates `Person` onto each book. After A3 the repository should return raw `Book` rows and `BookService` should attach borrowers/reservers.
- `Books.state` stores only Available/Borrowed. The combo value Reserved is a filter on `reserved_user_id` / `Book.is_reserved`, not a domain `BookState`.

<div dir="rtl">

**یک پروژه دانشگاهی که در آن یک سیستم مدیریت کتابخانه با استفاده از PyQT5 طراحی می‌شود و دارای قسمت‌های کاربر و ادمین است.**

# 💬 **نکات پروژه**

* عکس‌های برنامه در دایرکتوری ScreenShots قرار دارند.
* برای اجرا برنامه، به پایتون بالاتر از نسخه 3.6 نیاز دارید.
* کتابخانه‌های مورد نیاز در فایل requirements.txt قرار دارند.
* برای استفاده از برنامه، در صورتی که نیاز به اجرای تست‌ها دارید، قسمت **##====== while testing ======##** در ابتدای فایل‌های Code را uncomment کنید، در غیر این صورت قسمت **##====== while running ======##** را uncomment کنید.
* لطفا فایل Help.txt را مطالعه کنید. (یوزر و پسوردهای مورد نیاز در آن قرار دارد)
* برای دسترسی به همه‌ی پروژه‌های دانشگاهی من، به این لینک مراجعه کنید:

👈🏻 **[پروژه‌های دانشگاهی من](https://github.com/bestmahdi2/Uni__Bachelors_SKU_Path)**

# 📝 **توضیحات پروژه**
<img src="Project_Description.png" width="100%">

# 🖼 **عکس‌های پروژه**

<p align="center">
  <img src="ScreenShots/1. Pytest Results.png" width="70%">
  
  <img src="ScreenShots/2. Sign In.png" width="40%">
  
  <img src="ScreenShots/3. Sign Up.png" width="40%">

  <img src="ScreenShots/4. Officer Partition Notifications.png" width="70%">

  <img src="ScreenShots/5. Officer Partition Books State.png" width="70%">

  <img src="ScreenShots/6. Officer Partition New Officer.png" width="70%">

  <img src="ScreenShots/7. Costumer Partition Books.png" width="70%">

  <img src="ScreenShots/8. Costumer Partition My Books.png" width="70%">

  <img src="ScreenShots/9. Costumer Partition My Activity.png" width="70%">
</p>
</div>
