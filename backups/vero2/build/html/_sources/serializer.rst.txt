
stakeholder.serializers
-----------------------

.. automodule:: stakeholder.serializers
    :members:
    :undoc-members:
    :show-inheritance:


from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from cp_eav.models import DynamicTable
from cp_yodlee.models import CPYodlee
from payments.models import AdvanceOptions
from stakeholder.models import Stakeholder, GuestStakeholder, BusinessEntity, StakeholderInfo
from stakeholder.tasks import register_stakeholder
from users.models import CamelportUser
from users.serializers import CamelportUserSerializer


class StakeholderRegisterSerializer(serializers.ModelSerializer):
    user = CamelportUserSerializer()
    password1 = serializers.CharField(max_length=32, write_only=True)
    password2 = serializers.CharField(max_length=32, write_only=True)

    class Meta:
        model = Stakeholder
        fields = ('id',
                  'user',
                  'executive_first_name',
                  'executive_last_name',
                  'phone',
                  'mobile',
                  'password1',
                  'password2',
                  'dynamic_table',
                  'company_name',
                  'entity_type',
                  'pan_number',
                  'iec_code',
                  'company_address_line_1',
                  'company_address_line_2',
                  'company_address_line_3',
                  'city',
                  'state',
                  'country',
                  'zipcode',
                  'designation',
                  'reg_status',
                  )
        extra_kwargs = {
            'dynamic_table': {
                'write_only': True
            },
            'reg_status': {
                'write_only': True
            }
        }

    def validate_password1(self, value):

        if value != self.initial_data['password2']:
            raise serializers.ValidationError("The passwords do not match")

        return value

    def create(self, validated_data):

        user_data = validated_data.pop('user')
        user = CamelportUser.objects.create(**user_data)
        password = validated_data.pop('password1')
        validated_data.pop('password2')
        user.change_password(password)

        if 'dynamic_table' not in validated_data:
            validated_data['dynamic_table'], created = DynamicTable.objects.get_or_create(
                table_name='Shipper',
                content_type=ContentType.objects.get(model='stakeholder')
            )

        stakeholder = Stakeholder.objects.create(user=user, **validated_data)
        stakeholder = register_stakeholder(
            stk_id=stakeholder.id
        )

        AdvanceOptions.objects.create(stakeholder=stakeholder,
                                      percent=50,
                                      additive=0)

        CPYodlee.objects.create(stakeholder=stakeholder)
        # curl
        # https://camelportsupport.zendesk.com/api/v2/users.json

        ############

        #######create_helpscout_account(stk_id=stakeholder.id)
        return stakeholder


class StakeholderRegStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stakeholder
        fields = ('reg_status',
                  'is_enabled'
                  )


class ChildStakeholderSerializer(serializers.ModelSerializer):
    user = CamelportUserSerializer()

    password1 = serializers.CharField(max_length=32, write_only=True)
    password2 = serializers.CharField(max_length=32, write_only=True)
    role = serializers.IntegerField(write_only=True)

    class Meta:
        model = Stakeholder
        fields = (
            'executive_first_name',
            'executive_last_name',
            'user',
            'password1',
            'password2',
            'role',
            'is_enabled'
        )

    def validate(self, attrs):

        if attrs['password1'] != attrs['password2']:
            raise serializers.ValidationError({'password2': "The passwords do not match"})

        return attrs

    def validate_role(self, value):
        if value < 1 or value > 4:
            raise serializers.ValidationError('Role must be between 1 and 4 (included)')
        return value


class GuestStakeholderSerializer(serializers.ModelSerializer):
    child_stakeholder = ChildStakeholderSerializer()

    class Meta:
        model = GuestStakeholder
        fields = ('id', 'child_stakeholder')

    def create(self, validated_data):
        child_stakeholder_data = validated_data.pop('child_stakeholder')

        parent_stakeholder_instance = self.context['logged_in_stakeholder']

        role = child_stakeholder_data.pop('role')

        dynamic_table = DynamicTable.objects.get(table_name='Guest{}'.format(role))

        child_stakeholder_data['dynamic_table'] = dynamic_table
        child_stakeholder_data['user'] = CamelportUser.objects.create(**child_stakeholder_data['user'])

        child_stakeholder_data['user'].change_password(child_stakeholder_data.pop('password1'))
        child_stakeholder_data.pop('password2')

        child_stakeholder_data['company_name'] = parent_stakeholder_instance.company_name
        child_stakeholder_data['iec_code'] = parent_stakeholder_instance.iec_code
        child_stakeholder_data['company_address_line_1'] = parent_stakeholder_instance.company_address_line_1
        child_stakeholder_data['company_address_line_2'] = parent_stakeholder_instance.company_address_line_2
        child_stakeholder_data['company_address_line_3'] = parent_stakeholder_instance.company_address_line_3
        child_stakeholder_data['city'] = parent_stakeholder_instance.city
        child_stakeholder_data['state'] = parent_stakeholder_instance.state
        child_stakeholder_data['country'] = parent_stakeholder_instance.country
        child_stakeholder_data['zipcode'] = parent_stakeholder_instance.zipcode
        child_stakeholder_data['reg_status'] = parent_stakeholder_instance.reg_status

        child_stakeholder = Stakeholder.objects.create(**child_stakeholder_data)

        guest_obj = GuestStakeholder.objects.create(
            parent_stakeholder=parent_stakeholder_instance,
            child_stakeholder=child_stakeholder
        )

        return guest_obj


class StakeholderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stakeholder
        fields = ('id',
                  'executive_first_name',
                  'executive_last_name',
                  'phone',
                  'mobile',

                  'dynamic_table',
                  'company_name',
                  'entity_type',
                  'pan_number',
                  'iec_code',
                  'company_address_line_1',
                  'company_address_line_2',
                  'company_address_line_3',
                  'city',
                  'state',
                  'country',
                  'zipcode',
                  'designation',
                  'reg_status',
                  'is_enabled'
                  )

    def update(self, instance, validated_data):
        for key in validated_data:
            setattr(instance, key, validated_data[key])
        instance.save()
        return instance


class BusinessEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEntity
        fields = (
            'id',
            'corporate_identification_number',
            'date_of_registration',
            'company_name',
            'company_status',
            'company_class',
            'company_category',
            'authorized_capital',
            'paidup_capital',
            'registered_state',
            'registrar_of_companies',
            'principal_business_activity_as_per_cin',
            'registered_office_address',
            'sub_category'
        )


class ChildStakeholderListSerializer(serializers.ModelSerializer):
    user = CamelportUserSerializer()

    password1 = serializers.CharField(max_length=32, write_only=True)
    password2 = serializers.CharField(max_length=32, write_only=True)
    role = serializers.IntegerField(write_only=True)

    class Meta:
        model = Stakeholder
        fields = (
            'id',
            'executive_first_name',
            'executive_last_name',
            'user',
            'password1',
            'password2',
            'role',
            'is_enabled'
        )


class StakeholderFullSerializer(serializers.ModelSerializer):
    user = CamelportUserSerializer()

    class Meta:
        model = Stakeholder
        fields = ('id',
                  'user',
                  'executive_first_name',
                  'executive_last_name',
                  'phone',
                  'mobile',
                  'dynamic_table',
                  'company_name',
                  'entity_type',
                  'pan_number',
                  'iec_code',
                  'company_address_line_1',
                  'company_address_line_2',
                  'company_address_line_3',
                  'city',
                  'state',
                  'country',
                  'zipcode',
                  'designation',
                  'reg_status',
                  'quickbooks_customer',
                  'razor_pay',
                  'helpscout_id',
                  'is_enabled'
                  )

        extra_kwargs = {
            'executive_first_name': {
                'required': False

            },
            'executive_last_name': {
                'required': False

            }, 'phone': {
                'required': False

            }, 'mobile': {
                'required': False

            }, 'dynamic_table': {
                'required': False

            }, 'user': {
                'required': False
            },
        }


class StakeholderShortSerializer(serializers.ModelSerializer):
    user = CamelportUserSerializer()
    stakeholder_type = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Stakeholder
        fields = ('id',
                  'user',
                  'executive_first_name',
                  'executive_last_name',
                  'company_name',
                  'is_enabled',
                  'stakeholder_type'
                  )

        extra_kwargs = {
            'executive_first_name': {
                'required': False

            },
            'executive_last_name': {
                'required': False

            }, 'user': {
                'required': False
            },
        }

    def get_stakeholder_type(self, instance):
        return instance.user.stakeholder.dynamic_table.table_name


class StakeholderChangePasswordSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(max_length=32, write_only=True)
    password2 = serializers.CharField(max_length=32, write_only=True)

    class Meta:
        model = Stakeholder
        fields = (

            'password1',
            'password2'

        )

    def validate_password1(self, value):
        if value != self.initial_data['password2']:
            raise serializers.ValidationError("The passwords do not match")

        return value


class StakeholderInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StakeholderInfo
        fields = (
            'stakeholder',
            'rating',
            'age_of_company_years',
            'house_bl',
            'response_time_hr'

        )


class StakeholderDetailSerializer(serializers.ModelSerializer):
    user = CamelportUserSerializer()
    info = StakeholderInfoSerializer(source='get_stakeholder_info')

    class Meta:
        model = Stakeholder
        fields = (
            'id',
            'executive_first_name',
            'executive_last_name',
            'company_name',
            'user',
            'is_enabled',
            'info'
        )
