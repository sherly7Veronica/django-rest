task.serializers
-----------------------

.. automodule:: task.serializers
    :members:
    :undoc-members:
    :show-inheritance:

import json
from collections import OrderedDict
from copy import deepcopy

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.utils.serializer_helpers import BindingDict

from booking.models import CPBooking, Booking
from booking.serializer import CPBookingForActiveTaskSerializer
from rates.serializer import BidPagePenaltySerializer
from shipment.models import Shipment, ShipmentBooking
from stakeholder.serializers import StakeholderShortSerializer
from task.models import Task, AbstractTask, TaskFiles, FileUploads, FormElement, Form, TaskBaseModel, \
    FormElementValue, TaskVariable, FileFormElementValue  # TaskData


# class TaskDataLCSerializer(serializers.Serializer):
#     data = serializers.CharField(max_length=4096)
#
#     class Meta:
#         fields = (
#             'data'
#         )
#
#     def create(self, validated_data):
#         task = self.context['task']
#         task_data = TaskData.objects.create(task=task, **validated_data)
#         task.mark_as_completed()
#         return task_data


##########################################################

# @TODO: change file uploads to the new scheme of bulk upload of all files in a booking.


class AbstractTaskWithPenaltiesSerializer(serializers.ModelSerializer):
    penalties = BidPagePenaltySerializer(source='get_penalty_set', many=True)

    class Meta:
        model = AbstractTask
        fields = (
            'task_for',
            'expiry',
            'escalate_at',
            'mode_type',
            'hub_type',
            'is_incoming',
            'penalties',
            'estimated_completion_at'
        )


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileUploads
        fields = (
            'file_number',
            'file',
        )


class TaskFileUploadSerializer(serializers.Serializer):
    files = FileUploadSerializer(many=True)

    class Meta:
        fields = (
            'files',
        )

    parser_classes = (MultiPartParser,)

    def update(self, instance, validated_data):
        files = validated_data['files']

    def create(self, validated_data):
        task = self.context['task']
        task_files = TaskFiles.objects.create(task=task)

        for file_ in validated_data['files']:
            file_upload = FileUploads.objects.create(**file_)
            task_files.files.add(file_upload)

        task.mark_as_completed()
        return task_files


###################################################


# class TaskFileDownloadSerializer(serializers.ModelSerializer):
#     def create(self, validated_data):
#         task = self.context['task']
#         task_data = TaskData.objects.create(task=task, **validated_data)
#         task.mark_as_completed()
#         return task_data
#
#
# class AcknowledgementSerializer(serializers.ModelSerializer):
#     def create(self, validated_data):
#         task = self.context['task']
#         task_data = TaskData.objects.create(task=task, **validated_data)
#         task.mark_as_completed()
#         return task_data


class TaskSerializer(serializers.ModelSerializer):
    task_for = StakeholderShortSerializer()
    secondary_stakeholders = StakeholderShortSerializer(many=True)
    notify_stakeholders = StakeholderShortSerializer(many=True)
    booking = CPBookingForActiveTaskSerializer()
    completed_percentage = serializers.IntegerField(source='get_task_is_filled_percent')

    class Meta:
        model = Task
        fields = (
            'id',
            'task_name',
            'task_description',
            'dependency_tasks',
            'task_for',
            'triggered_at',
            'expiry',
            'escalation',
            'notify_stakeholders',
            'secondary_stakeholders',
            'task_type',
            'completed_percentage',
            'task_category',
            'is_active',
            'completed_at',
            'booking',
            'event',
            'trigger_tasks_on_completion',
            'abstract_task',
            'estimated_completion',
            'partially_completed_at',
            'expired_at',
        )

        # @TODO: add validation for task type (stakeholder & hubs allowed)

    def validate(self, data):
        triggered_at = data['trigger_tasks_on_completion']
        dependency_tasks = data['dependency_tasks']

        intersection = set(triggered_at).intersection(set(dependency_tasks))
        if len(intersection) > 0:
            raise serializers.ValidationError(
                {'trigger_tasks_on_completion': 'common task found in triggered_at and dependency_tasks'})

        return data


class TaskGantChartSerializer(serializers.ModelSerializer):
    task_for = StakeholderShortSerializer()
    secondary_stakeholders = StakeholderShortSerializer(many=True)
    notify_stakeholders = StakeholderShortSerializer(many=True)
    booking = CPBookingForActiveTaskSerializer()
    completed_percentage = serializers.IntegerField(source='get_task_is_filled_percent')
    can_edit = serializers.SerializerMethodField(read_only=True)
    can_view = serializers.SerializerMethodField(read_only=True)

    # completed_percentage = serializers.SerializerMethodField('get_task_is_filled_percent')
    class Meta:
        model = Task
        fields = (
            'id',
            'task_name',
            'task_description',
            'dependency_tasks',
            'task_for',
            'triggered_at',
            'expiry',
            'escalation',
            'notify_stakeholders',
            'secondary_stakeholders',
            'task_type',
            'is_active',
            'completed_at',
            'booking',
            'event',
            'trigger_tasks_on_completion',
            'abstract_task',
            'estimated_completion',
            'partially_completed_at',
            'completed_percentage',
            'expired_at',
            'can_edit',
            'can_view'
        )

    def get_can_view(self, instance):
        stakeholder = self.context['request'].user.stakeholder

        return instance.task_for == stakeholder \
               or instance.secondary_stakeholders.filter(pk=stakeholder.id).exists() \
               or instance.notify_stakeholders.filter(pk=stakeholder.id).exists()

    def get_can_edit(self, instance):
        stakeholder = self.context['request'].user.stakeholder

        return instance.task_for == stakeholder \
               or instance.secondary_stakeholders.filter(pk=stakeholder.id).exists()


class FormElementsSerializer(serializers.ModelSerializer):
    kwargs = serializers.DictField(source='get_kwargs_dict')

    class Meta:
        model = FormElement
        fields = (
            'id',
            'type',
            'css_class',
            'label',
            'placeholder',
            'name',
            'kwargs',
            'default',
            'order',
            'assign_to_var',
            'is_autofill',
            # 'is_editable'
        )

    def to_representation(self, instance):
        result = super(FormElementsSerializer, self).to_representation(instance)
        result['type'] = instance.get_type_display()
        # if instance.kwargs:
        #     result['kwargs'] = json.loads(instance.kwargs)
        return result

    def create(self, validated_data):
        validated_data['kwargs'] = json.dumps(validated_data.pop('get_kwargs_dict'))
        return FormElement.objects.create(**validated_data)


class FormElementsRetrieveSerializer(serializers.ModelSerializer):
    kwargs = serializers.DictField(source='get_kwargs_dict')
    value_present = serializers.SerializerMethodField(
        'get_is_form_element_filled')  # <=================================

    class Meta:
        model = FormElement
        fields = (
            'id',
            'type',
            'css_class',
            'label',
            'placeholder',
            'name',
            'kwargs',
            'default',
            'order',
            'assign_to_var',
            'is_autofill',
            'value_present'
        )

    def get_is_form_element_filled(self, obj):
        form_element = obj
        quote = self.context['task'].booking.quote
        s_num = self.context['s_num']
        is_filled = FormElementValue.objects.filter(
            shipment__shipment_num=self.context['s_num'],
            # form_element__form=form,
            form_element=form_element,
            shipment__shipper_quote=self.context['task'].booking.quote,
            task=self.context['task']
        ).count() >= 1
        return is_filled

    def to_representation(self, instance):
        result = super(FormElementsRetrieveSerializer, self).to_representation(instance)
        result['type'] = instance.get_type_display()

        result['default'] = instance.get_default_value(
            shipment_num=self.context['s_num'],
            task=self.context['task']
        )
        # if instance.kwargs:
        #     result['kwargs'] = json.loads(instance.kwargs)
        return result


class FormElementsListSerializer(serializers.ModelSerializer):
    kwargs = serializers.DictField(source='get_kwargs_dict')
    value_present = serializers.SerializerMethodField(
        'get_is_form_element_filled')  # <=================================

    class Meta:
        model = FormElement
        fields = (
            'id',
            'type',
            'css_class',
            'label',
            'placeholder',
            'name',
            'kwargs',
            'default',
            'order',
            'assign_to_var',
            'is_autofill',
            'value_present'
        )

    def get_is_form_element_filled(self, obj):
        form_element = obj
        quote = self.context['task'].booking.quote
        s_num = self.context['s_num']
        is_filled = FormElementValue.objects.filter(
            shipment__shipment_num=self.context['s_num'],
            # form_element__form=form,
            form_element=form_element,
            shipment__shipper_quote=self.context['task'].booking.quote,
            task=self.context['task']
        ).count() >= 1
        return is_filled

    def to_representation(self, instance):
        result = super(FormElementsListSerializer, self).to_representation(instance)
        result['type'] = instance.get_type_display()

        result['default'] = instance.get_default_value(
            shipment_num=self.context['s_num'],
            task=self.context['task']
        )
        # if instance.kwargs:
        #     result['kwargs'] = json.loads(instance.kwargs)
        return result


class FormSerializer(serializers.ModelSerializer):
    form_elements = FormElementsSerializer(source='get_elements', many=True, write_only=True)

    class Meta:
        model = Form
        fields = (
            'id',
            'name',
            'description',
            'form_elements'
        )

    def validate_form_elements(self, value):
        if len(value) > 0:
            for index, i in enumerate(value):
                j_values = value[index + 1:]
                for j in j_values:
                    if i["name"] == j["name"]:
                        raise ValidationError("Form elements should not have same name")
        return value


class FormRetrieveSerializer(serializers.ModelSerializer):
    form_elements = FormElementsRetrieveSerializer(source='get_elements', many=True)

    class Meta:
        model = Form
        fields = (
            'id',
            'name',
            'description',
            'form_elements'
        )


class FormElementValueDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormElementValue
        fields = (
            'id',
            'value',
            'shipment',
            'form_element'
        )


class AbstractTaskSerializer(serializers.ModelSerializer):  # Do not use for update

    form = FormSerializer(required=False)

    class Meta:
        model = AbstractTask
        fields = (
            'id',
            'task_name',
            'task_description',
            'task_type',

            'task_category',
            'task_for',
            'expiry',
            'escalate_at',

            'dependency_tasks',
            'trigger_tasks_on_completion',

            'mode_type',
            'hub_type',
            'is_incoming',

            'notify_stakeholders',
            'secondary_stakeholders',

            'notification_msg_short',
            'notification_msg_long',
            'notification_msg_title',

            'is_display_field',
            'display_name',
            'form',
            'trigger_tasks_on',
            'initiator_task',
            'estimated_completion_at'
        )
        extra_kwargs = {
            'mode_type': {
                'required': False
            },
            'hub_type': {
                'required': False
            },
            'is_incoming': {
                'required': False
            },
        }

    def validate(self, attrs):
        request = self.context['request']

        if request.method.upper() == 'PUT' or request.method.upper() == 'PATCH':
            return attrs

        if attrs['task_type'] == TaskBaseModel.TASK_TYPE_FORM:
            if attrs['form'] is None:
                raise serializers.ValidationError({
                    'form': ''
                })
            else:
                return attrs
        # else:
        #     if attrs['form'] is None:
        #         return attrs
        #     else:
        #         raise serializers.ValidationError({
        #             'form': ''
        #         })
        else:
            return attrs

    # def validate_mode_type(self, value):
    #     if value.content_type.id != 19:
    #         raise serializers.ValidationError('The dynamic table is not a mode')
    #
    #     return value
    #
    # def validate_hub_type(self, value):
    #     if value.content_type.id != 18:
    #         raise serializers.ValidationError('The dynamic table is not a hub')
    #
    #     return value

    def validate_display_name(self, value):
        if value == '':
            return None
        return value

    def create(self, validated_data):
        if 'form' in validated_data:
            form_data = validated_data.pop('form')

        form = None

        if validated_data['task_type'] == AbstractTask.TASK_TYPE_FORM:
            form_elements_data = form_data.pop('get_elements')
            form = Form.objects.create(**form_data)

            for form_element_data in form_elements_data:
                form_element_data['kwargs'] = json.dumps(form_element_data.pop('get_kwargs_dict'))
                FormElement.objects.create(form=form, **form_element_data)

        return AbstractTask.objects.create(form=form, **validated_data)


class TaskDataSerializer(serializers.Serializer):
    def __init__(self, task, shipment_num=None, is_create=False, **kwargs):
        super(TaskDataSerializer, self).__init__(**kwargs)

        self.task = task
        self.shipment_num = shipment_num
        self.shipment = Shipment.objects.get(
            shipper_quote=task.booking.quote,
            shipment_num=self.shipment_num
        )

        self.is_create = is_create

        self.required_count = 0

        # if self.shipment_num:
        #     self.instance = self._get_instance()

        self.field_form_element = {}

        self._declared_fields = self._get_declared_fields()

    def update_task_variable(self, form_element, value):

        if form_element.assign_to_var:

            if '[i]' in form_element.assign_to_var:
                index_type = TaskVariable.TYPE_INDEX_ALL
                index = self.shipment_num
            elif '[v]' in form_element.assign_to_var:
                index_type = TaskVariable.TYPE_INDEX_VENDOR
                # index = self.shipment_num
                bookings = self.task.leg.leg_booking
                booking = self.task.leg.leg_booking.get(shipmentbooking__shipment__shipment_num=self.shipment_num)
                index = booking.booking_index
            else:
                index_type = TaskVariable.TYPE_INDEX_NONE
                index = 0

            TaskVariable.objects.update_or_create(
                index_type=index_type,
                index=index,
                # value=value,
                cp_booking=self.shipment.shipper_quote.cpbooking,
                name=form_element.assign_to_var.replace('[i]', '').replace('[v]', ''),
                defaults={'value': value}
            )

            if form_element.assign_to_var == 'container_num':
                self.shipment.container_num = value
                self.shipment.save()

    def create_form_element_value(self, form_element, value, shipment):

        if self.task.task_category == Task.TASK_CATEGORY_BLOCKCHAIN and value:
            try:
                self.task.create_blockchain(shipment)
            except:
                pass

        try:
            self.task.make_booking_inactive(shipment)
        except:
            pass

        if form_element.type == FormElement.TYPE_CHOICE_FILE:
            fev_original = FormElementValue.objects.create(
                value='pending',
                shipment=shipment,
                form_element=form_element,
                task=self.task
            )

            file_doc = FileFormElementValue.objects.create(
                form_element_value=fev_original,
                doc=value
            )

            fev_original.value = file_doc.doc.url
            fev_original.save()

            return fev_original

        else:

            return FormElementValue.objects.create(
                value=value,
                shipment=shipment,
                form_element=form_element,
                task=self.task
            )

    def create(self, validated_data):

        request_stakeholder = self.context['request'].user.stakeholder

        # Checking Permissions
        ############
        if settings.STAKEHOLDER_TYPE[
            request_stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:
            if Shipment.objects.filter(
                    shipper_quote=self.task.booking.quote,
                    shipment_num=self.shipment_num,
                    shipment_booking__vendor_booking__service_provider=self.context['request'].user.stakeholder
            ).count() is not 1:
                raise serializers.ValidationError({'detail': 'not authorized'})

        if not self.task.task_for == request_stakeholder:
            raise serializers.ValidationError({'detail': 'this task is not for you'})
        ############

        value_flag = True

        if self.task.task_type == Task.TASK_TYPE_ACK:

            for v in validated_data.values():
                value_flag &= v

            if not value_flag:

                curr_task_copy = deepcopy(self.task)
                curr_task_copy.id = None
                curr_task_copy.is_active = True

                # curr_form = curr_task_copy.form
                # curr_form.id = None
                # curr_form.save()
                #
                # curr_task_copy.form = curr_form
                # curr_task_copy.formelementvalue_set.all().update(value=None)
                curr_task_copy.completed_percentage = 0
                curr_task_copy.save()

                curr_task_copy.trigger_tasks_on_completion.clear()
                curr_task_copy.dependency_tasks.clear()

                for trg in self.task.trigger_tasks_on_completion.all():
                    curr_task_copy.trigger_tasks_on_completion.add(trg)

                self.task.trigger_tasks_on_completion.clear()

                for task in self.task.dependency_tasks.all():
                    task.id = None
                    task.is_active = True
                    task.expiry = 4320
                    task.escalation = 2880
                    task.triggered_at = timezone.now()
                    task.completed_at = None
                    task.completed_percentage = 0
                    # task.is_active = True
                    # task.formelementvalue_set.all().update(value=None)
                    task.save()

                    task.trigger_tasks_on_completion.clear()

                    task.trigger_tasks_on_completion.add(curr_task_copy)
                    curr_task_copy.dependency_tasks.add(task)

        else:
            pass

        for key, value in validated_data.items():
            form_element = self.task.get_form_element_by_name(key)

            if form_element.is_autofill:

                shipment_set = Shipment.objects.filter(
                    shipper_quote=self.task.booking.quote
                )

                if self.task.is_task_for_vendor():
                    shipment_set.filter(
                        shipment_booking__vendor_booking__service_provider=request_stakeholder
                    )

                for shipment in shipment_set:
                    self.create_form_element_value(
                        form_element=form_element,
                        shipment=shipment,
                        value=value
                    )

                self.update_task_variable(
                    form_element=form_element,
                    value=value
                )
            else:
                self.create_form_element_value(
                    form_element=form_element,
                    shipment=self.shipment,
                    value=value
                )

                self.update_task_variable(
                    form_element=form_element,
                    value=value
                )

        completed_form_element_values = FormElementValue.objects.filter(
            form_element__form=self.task.form,
            shipment__shipper_quote=self.task.booking.quote,
            task=self.task
        )

        if self.task.is_task_for_vendor():
            completed_form_element_values = completed_form_element_values.filter(
                shipment__shipment_booking__vendor_booking__service_provider=request_stakeholder).distinct()
        else:
            completed_form_element_values = completed_form_element_values.filter(
                shipment__shipper_quote__stakeholder=request_stakeholder).distinct()

        if completed_form_element_values.count() >= self.task.form.formelement_set.filter(
                kwargs__icontains='"required: true"').distinct().count():
            self.task.mark_as_completed()

        ###################################################################################

        instance = self.task.get_form_data_instance(
            shipment_num=self.shipment_num,
        )

        if instance:
            self.task.mark_as_partially_completed()

        return instance

    def update(self, instance, validated_data):
        return instance.update(**validated_data)

    def _get_declared_fields(self):
        fields = []

        ###############################################################################

        for form_element in self.task.form.formelement_set.all().order_by('order'):
            field = TaskDataSerializer._get_field_by_form_element(form_element)
            self.field_form_element[form_element.name] = form_element

            if field:
                if form_element.is_autofill and FormElementValue.objects.filter(
                        form_element=form_element,
                        shipment=self.shipment,
                        task=self.task
                ):
                    if not self.is_create:
                        fields.append(field)
                else:
                    fields.append(field)

        ################################################################################

        # check_form_elements = []
        # for form_element in self.task.form.formelement_set.all().order_by('order'):
        #     check_form_elements.append(form_element.name)
        #
        # cfe = check_form_elements

        # for form_element in self.task.form.formelement_set.all().order_by('order'):
        #     try:
        #         form_element_value = FormElementValue.objects.get(
        #             form_element=form_element,
        #             shipment=self.shipment
        #         )
        #         field = TaskDataSerializer._get_field_by_form_element(form_element)
        #         self.field_form_element[form_element.name] = form_element
        #
        #         if field:
        #             fields.append(field)
        #     except:
        #         continue

        return OrderedDict(fields)

    @property
    def fields(self):
        """
        A dictionary of {field_name: field_instance}.
        """
        # `fields` is evaluated lazily. We do this to ensure that we don't
        # have issues importing modules that use ModelSerializers as fields,
        # even if Django's app-loading stage has not yet run.
        self._fields = BindingDict(self)
        for value in self.get_fields().items():
            self._fields[value[0]] = value[1]
            valueA = value[0]
            valueB = value[1]
            valueC = self._fields[value[0]]
            c = valueC
        return self._fields

    def _get_instance(self):
        return self.task.get_form_data_instance(self.shipment_num)

    @staticmethod
    def _get_field_by_form_element(form_element):

        if form_element.type == FormElement.TYPE_CHOICE_TEXT:
            return (
                form_element.name, serializers.CharField(
                    required=form_element.get_kwarg('required'),
                    max_length=form_element.get_kwarg('max_length'),
                    validators=form_element.get_validators()  # func(value)
                )
            )
        elif form_element.type == FormElement.TYPE_CHOICE_DECIMAL:
            return (
                form_element.name, serializers.DecimalField(
                    required=form_element.get_kwarg('required'),
                    max_digits=form_element.get_kwarg('max_digits'),
                    decimal_places=form_element.get_kwarg('decimal_places'),
                    validators=form_element.get_validators()  # func(value)
                )
            )
        elif form_element.type == FormElement.TYPE_CHOICE_CHOICE:
            return (
                form_element.name, serializers.CharField(
                    max_length=form_element.get_kwarg('max_length'),
                    required=form_element.get_kwarg('required'),
                    validators=form_element.get_validators()  # func(value)
                )
            )
        elif form_element.type == FormElement.TYPE_CHOICE_LAT_LNG:
            return (
                form_element.name, serializers.CharField(
                    required=form_element.get_kwarg('required'),
                    # max_length=26,
                    max_length=45,
                    validators=form_element.get_validators()  # func(value)
                )
            )

        elif form_element.type == FormElement.TYPE_CHOICE_FILE:
            return (
                form_element.name, serializers.FileField(
                    required=form_element.get_kwarg('required'),
                    validators=form_element.get_validators()  # func(value)
                )
            )
        elif form_element.type == FormElement.TYPE_CHOICE_CHECKBOX:
            return (
                form_element.name, serializers.NullBooleanField(
                    required=form_element.get_kwarg('required'),
                    validators=form_element.get_validators()  # func(value)
                )
            )

        elif form_element.type == FormElement.TYPE_CHOICE_DATETIME:
            return (
                form_element.name, serializers.DateTimeField(
                    required=form_element.get_kwarg('required'),
                    validators=form_element.get_validators(),  # func(value)
                )
            )

        elif form_element.type == FormElement.TYPE_CHOICE_INTEGER:
            return (
                form_element.name, serializers.IntegerField(
                    required=form_element.get_kwarg('required'),
                    max_value=form_element.get_kwarg('max_value'),
                    min_value=form_element.get_kwarg('min_value'),
                    validators=form_element.get_validators()  # func(value)
                )
            )

        return None


class TaskVariableSerializerModel:
    def __init__(self, var_names, cp_booking_id, stakeholder):
        self.var_names = var_names
        self.cp_booking_id = cp_booking_id
        self.stakeholder = stakeholder
        self.query_set = self.get_query_set()

    def get_query_set(self):

        ttvv = TaskVariable.objects.filter(cp_booking__quote__stakeholder=self.stakeholder).filter(
            Q(cp_booking_id=self.cp_booking_id) |
            Q(cp_booking__cp_booking_number=self.cp_booking_id)
        ).filter(name__in=self.var_names)
        ttvv2 = ttvv
        return ttvv

    def data(self):
        vars = {}
        # cp_booking = CPBooking.objects.get(pk=self.cp_booking_id)
        qs = self.query_set
        qs2 = qs
        check_var_names = self.var_names
        for var in self.query_set:
            # if var.is_indiced:
            #     vars.setdefault(
            #         var.name,
            #         {
            #             'name': var.name,
            #             'is_indiced': True,
            #             'values': []
            #         }
            #     )['values'].append(
            #         {
            #             'shipment_num': var.index,
            #             'value': var.value
            #         }
            #     )
            # else:
            #     vars[var.name] = {
            #         'name': var.name,
            #         'is_indiced': False,
            #         'value': var.value
            #     }

            if var.index_type == TaskVariable.TYPE_INDEX_ALL:
                vars.setdefault(
                    var.name,
                    {
                        'name': var.name,
                        'index_type': var.index_type,
                        'values': []
                    }
                )['values'].append(
                    {
                        'shipment_num': var.index,
                        'value': var.value
                    }
                )
                v = var
                vv = v
            elif var.index_type == TaskVariable.TYPE_INDEX_VENDOR:

                cpb = CPBooking.objects.get(pk=self.cp_booking_id)
                q = cpb.quote
                b = Booking.objects.get(quote=q, booking_index=var.index)
                sb = ShipmentBooking.objects.filter(vendor_booking=b)
                j = []
                for k in sb:
                    j.append(k.shipment.shipment_num)

                j.sort()
                # sb = ShipmentBooking.objects.filter(vendor_booking='4fb95b80-f35b-4126-af69-ee27f276e4dd')

                vars.setdefault(
                    var.name,
                    {
                        'name': var.name,
                        'index_type': var.index_type,
                        'values': []
                        # 'container_nos': []
                    }
                )['values'].append(
                    {
                        'booking_num': var.index,
                        'value': var.value,
                        # 'shipment_num': j.sort()
                        'shipment_num': j
                    }
                )
                # )['container_nos'].append(
                #     {
                #         'shiment_num':
                #     }
                # )
                v = var
                vv = v
            else:
                vars[var.name] = {
                    'name': var.name,
                    'index_type': TaskVariable.TYPE_INDEX_NONE,
                    'value': var.value
                }
                v = var
                vv = v
        return vars


