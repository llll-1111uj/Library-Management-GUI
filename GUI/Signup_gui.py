# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SignUpWindow(object):
    def setupUi(self, SignUpWindow):
        SignUpWindow.setObjectName("SignUpWindow")
        SignUpWindow.resize(640, 720)
        SignUpWindow.setMinimumSize(480, 560)
        SignUpWindow.setStyleSheet("background-color:#FFFFFF")

        self.label_logo = QtWidgets.QLabel(SignUpWindow)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(15)
        self.label_logo.setFont(font)
        self.label_logo.setText("")
        self.label_logo.setAlignment(QtCore.Qt.AlignCenter)
        self.label_logo.setMinimumHeight(72)
        self.label_logo.setObjectName("label_logo")

        self.label_3 = QtWidgets.QLabel(SignUpWindow)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(15)
        self.label_3.setFont(font)
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")

        self.frame = QtWidgets.QFrame(SignUpWindow)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        self.frame.setFont(font)
        self.frame.setStyleSheet("background-color:#F6F8FA;border-radius:0.7em;border :1px solid #D9DFE5;")
        self.frame.setFrameShape(QtWidgets.QFrame.Panel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Plain)
        self.frame.setLineWidth(2)
        self.frame.setMidLineWidth(4)
        self.frame.setObjectName("frame")

        def _field_label(name):
            label = QtWidgets.QLabel(self.frame)
            font = QtGui.QFont()
            font.setFamily("Segoe UI")
            font.setPointSize(12)
            label.setFont(font)
            label.setStyleSheet("background-color:#F6F8FA")
            label.setObjectName(name)
            return label

        def _line_edit(name, password=False):
            edit = QtWidgets.QLineEdit(self.frame)
            font = QtGui.QFont()
            font.setFamily("Segoe UI")
            edit.setFont(font)
            edit.setStyleSheet("border-radius:0.4em;border :1px solid #D7DDE3;")
            edit.setClearButtonEnabled(True)
            edit.setMinimumHeight(41)
            if password:
                edit.setEchoMode(QtWidgets.QLineEdit.Password)
            edit.setObjectName(name)
            return edit

        self.label = _field_label("label")
        self.lineEdit_username = _line_edit("lineEdit_username")
        self.lineEdit_username.setText("")
        self.label_2 = _field_label("label_2")
        self.lineEdit_password = _line_edit("lineEdit_password", True)
        self.label_4 = _field_label("label_4")
        self.lineEdit_password_2 = _line_edit("lineEdit_password_2", True)
        self.label_5 = _field_label("label_5")
        self.lineEdit_full_name = _line_edit("lineEdit_full_name")
        self.label_6 = _field_label("label_6")
        self.lineEdit_email = _line_edit("lineEdit_email")
        self.label_7 = _field_label("label_7")
        self.lineEdit_phone = _line_edit("lineEdit_phone")

        self.label_error = QtWidgets.QLabel(self.frame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.label_error.setFont(font)
        self.label_error.setStyleSheet("background-color:#F6F8FA;color:red")
        self.label_error.setText("")
        self.label_error.setObjectName("label_error")

        self.pushButton_Signup = QtWidgets.QPushButton(self.frame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.pushButton_Signup.setFont(font)
        self.pushButton_Signup.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_Signup.setStyleSheet("border-radius:0.4em;border :1px solid #D7DDE3;background-color:#2DA44E;color:white")
        self.pushButton_Signup.setAutoDefault(False)
        self.pushButton_Signup.setMinimumHeight(41)
        self.pushButton_Signup.setObjectName("pushButton_Signup")

        self.pushButton_signin = QtWidgets.QPushButton(self.frame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.pushButton_signin.setFont(font)
        self.pushButton_signin.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_signin.setStyleSheet("color:#0969DA")
        self.pushButton_signin.setFlat(True)
        self.pushButton_signin.setObjectName("pushButton_signin")

        form = QtWidgets.QVBoxLayout(self.frame)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(6)
        for widget in (
            self.label, self.lineEdit_username,
            self.label_2, self.lineEdit_password,
            self.label_4, self.lineEdit_password_2,
            self.label_5, self.lineEdit_full_name,
            self.label_6, self.lineEdit_email,
            self.label_7, self.lineEdit_phone,
            self.label_error, self.pushButton_Signup, self.pushButton_signin,
        ):
            form.addWidget(widget)

        form_col = QtWidgets.QWidget(SignUpWindow)
        form_col.setMaximumWidth(440)
        form_col.setMinimumWidth(320)
        col_layout = QtWidgets.QVBoxLayout(form_col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(8)
        col_layout.addWidget(self.label_logo)
        col_layout.addWidget(self.label_3)
        col_layout.addWidget(self.frame)

        scroll = QtWidgets.QScrollArea(SignUpWindow)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(form_col)
        scroll.setMaximumWidth(480)

        h_center = QtWidgets.QHBoxLayout()
        h_center.addStretch(1)
        h_center.addWidget(scroll)
        h_center.addStretch(1)

        outer = QtWidgets.QVBoxLayout(SignUpWindow)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.addStretch(1)
        outer.addLayout(h_center, 1)
        outer.addStretch(1)

        self.retranslateUi(SignUpWindow)
        self.pushButton_signin.clicked.connect(SignUpWindow.close)
        QtCore.QMetaObject.connectSlotsByName(SignUpWindow)
        SignUpWindow.setTabOrder(self.lineEdit_username, self.lineEdit_password)
        SignUpWindow.setTabOrder(self.lineEdit_password, self.lineEdit_password_2)
        SignUpWindow.setTabOrder(self.lineEdit_password_2, self.lineEdit_full_name)
        SignUpWindow.setTabOrder(self.lineEdit_full_name, self.lineEdit_email)
        SignUpWindow.setTabOrder(self.lineEdit_email, self.lineEdit_phone)
        SignUpWindow.setTabOrder(self.lineEdit_phone, self.pushButton_signin)
        SignUpWindow.setTabOrder(self.pushButton_signin, self.pushButton_Signup)

    def retranslateUi(self, SignUpWindow):
        _translate = QtCore.QCoreApplication.translate
        SignUpWindow.setWindowTitle(_translate("SignUpWindow", "Dialog"))
        self.label_4.setText(_translate("SignUpWindow", "Confirm Password"))
        self.label_5.setText(_translate("SignUpWindow", "Full Name"))
        self.lineEdit_phone.setStatusTip(_translate("SignUpWindow", "Enter your phone number"))
        self.lineEdit_password_2.setStatusTip(_translate("SignUpWindow", "Confirm the password"))
        self.lineEdit_password.setStatusTip(_translate("SignUpWindow", "Enter a password"))
        self.lineEdit_username.setStatusTip(_translate("SignUpWindow", "Enter your username"))
        self.label_2.setText(_translate("SignUpWindow", "Password"))
        self.pushButton_Signup.setStatusTip(_translate("SignUpWindow", "Click to sign up ..."))
        self.pushButton_Signup.setText(_translate("SignUpWindow", "Sign up"))
        self.label.setText(_translate("SignUpWindow", "Username"))
        self.label_7.setText(_translate("SignUpWindow", "Phone Number"))
        self.lineEdit_email.setStatusTip(_translate("SignUpWindow", "Enter your email address"))
        self.label_6.setText(_translate("SignUpWindow", "Email Address"))
        self.label_3.setText(_translate("SignUpWindow", "Sign up to Library Manager"))
        self.lineEdit_full_name.setStatusTip(_translate("SignUpWindow", "Enter your full name"))
        self.pushButton_signin.setStatusTip(_translate("SignUpWindow", "Click to sign in ..."))
        self.pushButton_signin.setText(_translate("SignUpWindow", "Already have an account ..."))


if __name__ == "__main__":
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    sys.path.insert(0, root)
    sys.path.insert(0, os.path.join(root, "Code"))

    from GUIManager import main

    main()
