# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import re
from random import randint

import requests
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cp_eav.generic_model_serializer import serializer_factory
from cp_eav.models import DynamicTable
from cp_eav.serializer import DynamicTableSerializer
from stakeholder import serializers as stakeholder_serializers
from stakeholder.models import Stakeholder, GuestStakeholder, BusinessEntity, StakeholderInfo, EmailVerifyToken
from stakeholder.serializers import StakeholderRegStatusSerializer, BusinessEntitySerializer, \
    StakeholderFullSerializer, \
    StakeholderUpdateSerializer, StakeholderChangePasswordSerializer, StakeholderDetailSerializer, \
    StakeholderInfoSerializer
from stakeholder.tasks import send_template
from users import serializers as user_serializers
from users.models import CamelportUser, ChangePasswordToken
from users.serializers import EmailVerificationSerializer
from utils.mail import SendGridHelper


class RegisterView(generics.CreateAPIView):
    """
    This view is to register a new stakeholder.
    """
    notification_functions = ['sendgrid_notif']
    notification_on = ['create']
    serializer_class = stakeholder_serializers.StakeholderRegisterSerializer

    def create(self, request, *args, **kwargs):
        """

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        Token.objects.create(user=serializer.instance.user)
        StakeholderInfo.objects.create(stakeholder=serializer.instance)

        # session = Session.objects.create(stakeholder=serializer.instance)

        email_token = EmailVerifyToken.objects.create(stakeholder=serializer.instance)

        self.send_verification_email(
            stk_instance=serializer.instance,
            email_verification_url=settings.EMAIL_VERIFY_URL.format(
                token=email_token.token
            )
        )

        response_data = serializer.data

        response_data['dynamic_table'] = serializer.instance.dynamic_table.table_name
        response_data['reg_status'] = serializer.instance.reg_status
        response_data['is_enabled'] = serializer.instance.is_enabled
        response_data['razor_pay'] = serializer.instance.razor_pay
        response_data['razor_account_number'] = serializer.instance.razor_account_number
        response_data['razor_ifsc_code'] = serializer.instance.razor_ifsc_code
        response_data['quickbooks_customer'] = serializer.instance.quickbooks_customer
        response_data['helpscout_id'] = serializer.instance.helpscout_id

        return Response(response_data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def sendgrid_notif(self, instance):
        response = SendGridHelper().send_template(
            template_id='c1a0dc3f-c619-487f-8759-c843ea8b45a7',
            email_to=instance.user.email,
            subject="Welcome to Camelport",
            substitutions={
                'name': instance.executive_first_name
            }
        )
        return response

    def send_verification_email(self, stk_instance, email_verification_url):
        send_template(
            template_id='c1a0dc3f-c619-487f-8759-c843ea8b45a7',
            email_to=stk_instance.user.email,
            subject="Welcome to Camelport",
            substitutions={
                'name': stk_instance.executive_first_name,
                'email_verification_url': email_verification_url
            }
        )

class Check_Is_EnabledView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request, *args, **kwargs):
        return Response({'pricing_plan': request.user.stakeholder.pricing_plan})


class LoginView(generics.CreateAPIView):
    serializer_class = user_serializers.CamelportUserLoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        if serializer.instance.stakeholder.dynamic_table.table_name in ['Guest1', 'Guest2', 'Guest3', 'Guest4']:
            token = Token.objects.get(
                user=serializer.instance.stakeholder.guest_child_stakeholder.parent_stakeholder.user)

        else:
            token, created = Token.objects.get_or_create(user=serializer.instance)

        stakeholder_serializer = StakeholderFullSerializer(instance=serializer.instance.stakeholder)
        # session = Session.objects.create(stakeholder=serializer.instance.stakeholder,
        #                                  expires_on=timezone.now() + timezone.timedelta(days=1))
        response_data = stakeholder_serializer.data

        response_data['token'] = {'key': token.key}

        response_data['dynamic_table'] = serializer.instance.stakeholder.dynamic_table.table_name
        response_data['reg_status'] = serializer.instance.stakeholder.reg_status
        response_data['is_enabled'] = serializer.instance.stakeholder.is_enabled
        response_data['razor_pay'] = serializer.instance.stakeholder.razor_pay
        response_data['razor_account_number'] = serializer.instance.stakeholder.razor_account_number
        response_data['razor_ifsc_code'] = serializer.instance.stakeholder.razor_ifsc_code
        response_data['quickbooks_customer'] = serializer.instance.stakeholder.quickbooks_customer
        response_data['helpscout_id'] = serializer.instance.stakeholder.helpscout_id
        # response_data['session_id'] = session.id

        ##
        # parent_stakeholder = serializer.instance.stakeholder.guest_child_stakeholder
        try:
            guest_stakeholder = GuestStakeholder.objects.get(child_stakeholder__id=response_data['id'])

            p_stakeholder = guest_stakeholder.parent_stakeholder
            if p_stakeholder:
                response_data['parent_stakeholder_type'] = p_stakeholder.dynamic_table.table_name
                response_data['guest_stakeholder_type'] = guest_stakeholder.name
                response_data['reg_status'] = p_stakeholder.reg_status
        except:
            pass

        return Response(
            response_data,
            status=status.HTTP_200_OK,
            headers=headers)


# class LoginView(generics.CreateAPIView):
#    serializer_class = user_serializers.CamelportUserLoginSerializer
#
#    def create(self, request, *args, **kwargs):
#        serializer = self.get_serializer(data=request.data)
#        serializer.is_valid(raise_exception=True)
#        self.perform_create(serializer)
#        headers = self.get_success_headers(serializer.data)
#
#        firebase_token, created = firebase_token.objects.get_or_create(user=serializer.instance)
#
#        return Response({'key': firebase_token.key,
#                         'email': serializer.instance.email}, status=status.HTTP_200_OK, headers=headers)


class StakeholderZendeskView(generics.RetrieveAPIView):
    def get_object(self):
        return get_object_or_404(Stakeholder, zendesk_id=self.kwargs['zendesk_id'])

    def get_serializer(self, *args, **kwargs):
        obj = self.get_object()


class StakeholderDynamicValueRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        qs = Stakeholder.objects.all()
        return qs

    def get_serializer(self, *args, **kwargs):
        dynamic_table = self.get_object().dynamic_table

        ser = serializer_factory(
            mdl=Stakeholder,
            fields=Stakeholder.get_fields_list(),
            dyn_table=dynamic_table,
        )
        return ser(*args, **kwargs)


class GuestStakeholderView(generics.ListCreateAPIView):
    serializer_class = stakeholder_serializers.GuestStakeholderSerializer

    def get_serializer_context(self):
        context = super(GuestStakeholderView, self).get_serializer_context()
        context['logged_in_stakeholder'] = self.request.user.stakeholder
        return context

    def get_queryset(self):
        return GuestStakeholder.objects.filter(guest_child_stakeholder__parent_stakeholder__user=self.request.user)


class GuestStakeholderRUDView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StakeholderFullSerializer

    def get_queryset(self):
        return Stakeholder.objects.filter(guest_child_stakeholder__parent_stakeholder__user=self.request.user)


class StakeholderTypeView(generics.ListAPIView):
    serializer_class = DynamicTableSerializer

    def get_queryset(self):
        return DynamicTable.objects.filter(content_type=ContentType.objects.get(model='stakeholder'))


class StakeholderRegStatusUpdateView(generics.UpdateAPIView):
    serializer_class = StakeholderRegStatusSerializer

    def get_queryset(self):
        return Stakeholder.objects.all()

    def get_object(self):
        return self.request.user.stakeholder


class StakeholderUpdateView(generics.UpdateAPIView):
    serializer_class = StakeholderFullSerializer

    def get_queryset(self):
        return Stakeholder.objects.all()

    def get_object(self):
        return self.request.user.stakeholder

    def get_serializer(self, *args, **kwargs):
        data = self.request.data
        if 'dynamic_table' in data:
            data.pop('dynamic_table')

        if 'user' in data:
            data.pop('user')

        kwargs['data'] = data

        return StakeholderUpdateSerializer(*args, **kwargs)


class StakeholderRetrieveView(generics.RetrieveAPIView):
    serializer_class = StakeholderFullSerializer

    def get_queryset(self):
        return Stakeholder.objects.all()

    def get_object(self):
        return self.request.user.stakeholder


class BusinessEntityAutocompleteView(generics.ListAPIView):
    serializer_class = BusinessEntitySerializer

    def get_queryset(self):

        search_text = self.request.query_params.get('search')

        query = self.get_query(search_text.split(" "), 'AND')

        query_set = BusinessEntity.objects.raw(query)

        result = list(query_set)

        if len(result) == 0:
            query = self.get_query(search_text.split(" "), 'OR')

            query_set = BusinessEntity.objects.raw(query)

            result = list(query_set)

        return result

    def get_query(self, texts, appender):

        lexeme_search = """to_tsquery('simple', (
                      SELECT string_agg(word, '|')
                      FROM company_unique_lexeme
                      WHERE similarity(word, '{text}')> 0.72)
                    )"""

        search_condition_boiler_plate = """{amp} document @@ {lexeme_search}"""

        order_by_boilder_plate = """{comma} ts_rank(document, to_tsquery('simple', (
                      SELECT string_agg(word, '|')
                      FROM company_unique_lexeme
                      WHERE similarity(word, '{text}')> 0.72))
                      )"""

        order_by = search_condition = ''

        for index, text in enumerate(texts):
            if index == 0:
                amp = ''
                comma = ''
            else:
                amp = appender
                comma = ', '

            text = text.replace("'", "''")

            search_condition = search_condition + search_condition_boiler_plate.format(
                lexeme_search=lexeme_search.format(text=text),
                amp=amp
            )

            order_by = order_by + order_by_boilder_plate.format(text=text, comma=comma)

        return """SELECT 
                      id, company_name
                    FROM company_name_index
                    WHERE {condition}
                    ORDER BY {order_by}
                    DESC LIMIT 10;""".format(condition=search_condition, order_by=order_by)


class SendOTPView(APIView):
    def post(self, request, *args, **kwargs):
        otp = randint(1000, 9999)
        mydict = {
            'authkey': settings.MOBILEAUTHKEY,
            'mobile': request.data['mobile'],
            'message': "Your OTP for registration on Camelport X is {}".format(otp),
            'sender': 'CMPORT',
            'country': '0',
            'otp': otp
        }

        headers = {'Content-Type': 'application/json'}
        # req = request
        r = requests.post(
            url='http://api.msg91.com/api/sendotp.php',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            # headers=headers,
            data=mydict
        )
        rr = json.loads(r.text)
        return Response(rr, r.status_code)

        # return Response(customer_created)


class SendOTPEwayBillView(APIView):
    def post(self, request, *args, **kwargs):
        otp = randint(1000, 9999)
        mydict = {
            'authkey': settings.MOBILEAUTHKEY,
            'mobile': request.data['mobile'],
            'message': "Your OTP for registration on Go Eway Bill is {}".format(otp),
            'sender': 'GOEWYB',
            'country': '0',
            'otp': otp
        }

        headers = {'Content-Type': 'application/json'}
        # req = request
        r = requests.post(
            url='http://api.msg91.com/api/sendotp.php',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            # headers=headers,
            data=mydict
        )
        rr = json.loads(r.text)
        return Response(rr, r.status_code)

        # return Response(customer_created)


# class SendOTPView(APIView):
#     def post(self, request, *args, **kwargs):
#         otp = randint(1000, 9999)
#         mydict = {
#             'authkey': settings.MOBILEAUTHKEY,
#             'mobile': request.data['mobile'],
#             'message': "Your OTP for registration on Camelport X is {}".format(otp),
#             'sender': 'CMPORT',
#             'country': '0',
#             'otp': otp
#         }
#
#         headers = {'Content-Type': 'application/json'}
#         # req = request
#         r = requests.post(
#             url='http://api.msg91.com/api/sendotp.php',
#             # auth=('authkey', settings.MOBILEAUTHKEY),
#             # headers=headers,
#             data=mydict
#         )
#         rr = r
#         return r.content

class VerifyOTPView(APIView):
    def post(self, request, *args, **kwargs):
        # otp = randint(1000, 9999)
        mydict = {
            'authkey': settings.MOBILEAUTHKEY,
            'mobile': request.data['mobile'],
            'country': '0',
            'otp': request.data['otp']
        }

        headers = {'Content-Type': 'application/json'}
        # req = request
        r = requests.post(
            url='http://api.msg91.com/api/verifyRequestOTP.php',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            # headers=headers,
            data=mydict
        )
        rr = json.loads(r.text)
        return Response(rr, r.status_code)


class RetryOTPView(APIView):
    def post(self, request, *args, **kwargs):
        # otp = randint(1000, 9999)
        mydict = {
            'authkey': settings.MOBILEAUTHKEY,
            'mobile': request.data['mobile'],
            'country': '0',
            'retrytype': 'text',
            # 'otp': request.data['otp']
        }

        headers = {'Content-Type': 'application/json'}
        # req = request
        r = requests.post(
            url='http://api.msg91.com/api/retryotp.php',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            # headers=headers,
            data=mydict
        )
        rr = json.loads(r.text)
        return Response(rr, r.status_code)


class VerifyEmailView(APIView):

    def post(self, request, *args, **kwargs):

        email = request.data.get('email', 'gibberish')

        email_unique = not CamelportUser.objects.filter(email__iexact=email).exists()
        email_valid = re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

        verified = email_unique and email_valid

        response_dict = {
            'verified': verified
        }

        if verified:
            response_dict['message'] = 'Email verified successfully'
        else:

            if not email_unique:
                response_dict['message'] = 'User with this email already exists'
            if not email_valid:
                response_dict['message'] = 'Invalid Email'

        return Response(response_dict)


class EWayBillGSTView(APIView):
    def get(self, request, *args, **kwargs):
        headers = {
            "Content-Type": "application/json"
        }
        mydict = {
            'gstin': kwargs["gst"]
        }

        response = requests.post(
            url='https://ewaybill.nic.in/BillGeneration/BillGeneration.aspx/GetGSTNDetails',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            headers=headers,
            # params=params,
            data=json.dumps(mydict)
        )
        if 199 < response.status_code < 300:
            response_dict = json.loads(response.text)
            if response_dict['d']:
                return Response(response_dict['d'])
            else:
                return Response({}, status.HTTP_404_NOT_FOUND)
        else:
            return Response({}, status.HTTP_404_NOT_FOUND)


class inttra_auth_check(APIView):
    def post(self, request, *args, **kwargs):
        # params = {"emailId":"","username":"ALBERT_825135","sessionKey":"","oldPassword":"","languageId":"1","password":"sjku@123","requestUrl":""}
        params = {
            "emailId": "",
            "username": request.data['username'],
            "sessionKey": "",
            "oldPassword": "",
            "languageId": "1",
            "password": request.data['password'],
            "requestUrl": ""
        }
        r = requests.post(
            url='https://www.ship.inttra.com/portal/authenticate',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            # headers=headers,
            params=params,
        )
        return Response(json.loads(r.text), r.status_code)


class itekseal_auth_check(APIView):
    def post(self, request, *args, **kwargs):
        # params = {"emailId":"","username":"ALBERT_825135","sessionKey":"","oldPassword":"","languageId":"1","password":"sjku@123","requestUrl":""}
        params = {
            "sTag": "TAG_1520082718669",
            "sExtraInfo": "Something Extra",
            "sAppId": "3792c1ca-7a6d-4cf2-bbf8-4c838715f2dc",
            "sUserName": "vaibhav",
            # "sUserName": request.data['username'],
            "sLoginId": "vaibhav",
            "sPasswordHash": "401b09eab3c013d4ca54922bb802bec8fd5318192b0a75f201d8b3727429080fb337591abd3e44453b954555b7a0812e1081c39b740293f765eae731f5a65ed1",
            # "sPasswordHash": request.data['password'],
            "sClientInfo": "",
            "sIP": ""
        }
        params = request.data
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        r = requests.post(
            url='https://www.itekseal.com/rseal/Auth/Login',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            headers=headers,
            params=params,
        )
        return Response(json.loads(r.text), r.status_code)


class odex_auth_check(APIView):
    def post(self, request, *args, **kwargs):
        # params = {"emailId":"","username":"ALBERT_825135","sessionKey":"","oldPassword":"","languageId":"1","password":"sjku@123","requestUrl":""}
        params = {
            "compLocId": "",
            "loginId": "vaibhav",
            "password": "ASDF",
            "email": ""
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        r = requests.post(
            url='https://odex.co/authenticateLogin.do',
            # auth=('authkey', settings.MOBILEAUTHKEY),
            headers=headers,
            params=params,
        )
        return Response(json.loads(r.text), r.status_code)


class GuestStakeholderListView(generics.ListAPIView):
    pagination_class = None
    serializer_class = StakeholderFullSerializer

    def get_queryset(self):
        return Stakeholder.objects.filter(guest_child_stakeholder__parent_stakeholder__user=self.request.user)


class ChangePasswordRequestView(APIView):
    def post(self, request, *args, **kwargs):
        #  validate
        if 'email' in request.data:
            user = get_object_or_404(CamelportUser, email=request.data.get('email'))
            pass_token, created = ChangePasswordToken.objects.get_or_create(
                user=user
            )
            params = {
                'url': settings.CHANGE_PASSWORD_URL.format(token=pass_token.token)
            }

            # send_template(
            send_template(
                template_id='0991778d-d8a1-4e5f-ba85-308a81632775',
                substitutions=params,
                email_to=request.data.get('email'),
                subject='Password Reset'
            )

            return Response({'status': 'success'})
        else:
            return Response({
                'status': 'failure',
                'message': 'email is a mandatory field'
            })


class ChangeStakeholderPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = StakeholderChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password1']

        token = kwargs['token']

        cp_token = get_object_or_404(ChangePasswordToken, token=token)

        cp_token.change_password(password)

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        token = kwargs['token']

        cp_token = get_object_or_404(ChangePasswordToken, token=token)

        serializer = StakeholderDetailSerializer(instance=cp_token.user.stakeholder)

        return Response(serializer.data)


class ChangeUserPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = StakeholderChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password1']
        user = request.user
        user.change_password(password)
        return Response({'status': 'success'})


class StakeholderInfoRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = StakeholderInfoSerializer

    def get_queryset(self):
        return StakeholderInfo.objects.all()

    def get_object(self):
        try:
            return self.request.user.stakeholder.stakeholderinfo
        except Exception as exc:
            raise Http404


class EmailVerifyView(generics.CreateAPIView):
    serializer_class = EmailVerificationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
