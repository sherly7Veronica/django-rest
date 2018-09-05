task.models
-----------------------

.. automodule:: task.models
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import re
import sys
import time

import dateutil.parser
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from blockchain.helpers import create_new_transaction
from events.models import Events
from notification.models import Notification
from quote.models import Leg
from shipment.models import ShipmentBooking
from stakeholder.models import Stakeholder
# from task.views import TaskDataOptionsRetreiveView
from utils.models import DateBaseModel


class FormData:
    def __init__(self, task, shipment_num, **kwargs):
        self.task = task
        self.shipment_num = shipment_num
        self.kwargs = kwargs
        self.form_elements_values = self._get_form_element_values()
        self._set_values()

    def _get_form_element_values(self):

        fev = FormElementValue.objects.filter(
            task=self.task,
            shipment__shipment_num=self.shipment_num,
            shipment__shipper_quote=self.task.booking.quote
        ).distinct().order_by('form_element__order')
        return fev

    def get_form_elements(self):
        return FormElement.objects.filter(
            form__task=self.task
        ).order_by('form_element__order')

    def _set_values(self):

        for element_value in self.form_elements_values:
            setattr(self, element_value.form_element.name, element_value.get_type_casted_value(self.task))

    def save(self, **kwargs):

        for element_value in self.form_elements_values:
            value = getattr(self, element_value.form_element.name, None)

            if value:
                element_value.value = value
                element_value.save()

        return self

    def update(self, **kwargs):

        for attr, value in kwargs:
            setattr(self, attr, value)

        return self.save()

    def delete(self, **kwargs):
        for element_value in self.form_elements_values:
            element_value.delete()
        return self


class TaskBaseModel(DateBaseModel):
    TASK_TYPE_ACK = 0
    TASK_TYPE_FORM = 1
    TASK_TYPE_INITIATOR = 2
    TASK_TYPE_FINAL = 4
    TASK_TYPE_BLOCKCHAIN = 3
    TASK_TYPE_PRECURSOR = -1

    TASK_TYPE_CHOICES = (
        (TASK_TYPE_PRECURSOR, 'precursor'),
        (TASK_TYPE_ACK, 'acknowledgement'),
        (TASK_TYPE_FORM, 'form'),
        (TASK_TYPE_INITIATOR, 'initiator'),
        (TASK_TYPE_BLOCKCHAIN, 'blockchain'),
        (TASK_TYPE_FINAL, 'final')
    )

    TASK_CATEGORY_NORMAL = 0
    TASK_CATEGORY_INITIATOR = 1
    TASK_CATEGORY_BLOCKCHAIN = 2
    TASK_CATEGORY_PRECURSOR = 3
    TASK_CATEGORY_FINAL = 4

    TASK_CATEGORY_CHOICES = (
        (TASK_CATEGORY_NORMAL, 'normal'),
        (TASK_CATEGORY_INITIATOR, 'initiator'),
        (TASK_CATEGORY_BLOCKCHAIN, 'blockchain'),
        (TASK_CATEGORY_PRECURSOR, 'precursor'),
        (TASK_CATEGORY_FINAL, 'final'),
    )

    TASK_TRIGGER_COMPLETED = 0
    TASK_TRIGGER_PARTIALLY_COMPLETED = 1
    TASK_TRIGGER_ESCALATED = 2
    TASK_TRIGGER_EXPIRED = 3

    TASK_TRIGGER_ON_CHOICES = (
        (TASK_TRIGGER_COMPLETED, 'completed'),
        (TASK_TRIGGER_PARTIALLY_COMPLETED, 'partially_completed'),
        (TASK_TRIGGER_ESCALATED, 'escalated'),
        (TASK_TRIGGER_EXPIRED, 'expired'),
    )

    task_name = models.CharField(max_length=64)
    task_description = models.CharField(max_length=1024)
    # task_for =
    # notify_stakeholders =
    task_type = models.IntegerField(default=TASK_TYPE_ACK, choices=TASK_TYPE_CHOICES)
    form = models.ForeignKey('task.Form', blank=True, null=True)
    trigger_tasks_on = models.IntegerField(default=TASK_TRIGGER_COMPLETED, choices=TASK_TRIGGER_ON_CHOICES)
    # is_active =
    # completed_at =
    # event =
    # trigger_tasks_on_completion =
    task_category = models.IntegerField(choices=TASK_CATEGORY_CHOICES, default=TASK_CATEGORY_NORMAL)

    def __str__(self):
        return self.task_name.encode('utf8', 'ignore')

    class Meta:
        abstract = True


class AbstractTask(TaskBaseModel):
    task_for = models.TextField()
    expiry = models.BigIntegerField(blank=True, null=True)
    escalate_at = models.BigIntegerField(blank=True, null=True)
    estimated_completion_at = models.BigIntegerField()

    dependency_tasks = models.ManyToManyField('task.AbstractTask', blank=True, null=True,
                                              related_name='dependent_tasks')
    trigger_tasks_on_completion = models.ManyToManyField('task.AbstractTask', blank=True, null=True,
                                                         related_name='triggered_tasks')

    mode_type = models.ForeignKey('cp_eav.DynamicTable', null=True, blank=True, related_name='mode_abstract_task')
    hub_type = models.ForeignKey('cp_eav.DynamicTable', null=True, blank=True, related_name='mode_abstract_hub')
    is_incoming = models.NullBooleanField()

    is_display_field = models.BooleanField(default=False)
    display_name = models.CharField(unique=True, blank=True, null=True, max_length=64)

    notify_stakeholders = models.TextField()

    secondary_stakeholders = models.TextField(blank=True)

    notification_msg_short = models.CharField(max_length=120)
    notification_msg_long = models.TextField()
    notification_msg_title = models.CharField(max_length=120)

    initiator_task = models.NullBooleanField(blank=True, null=True, default=None)

    is_enabled = models.BooleanField(default=True)
    enabled = models.BooleanField(default=False)
    order_number = models.IntegerField(default=0)
    include_for_type = models.CharField(max_length=512, blank=True, null=True)

    def __str__(self):
        mode = ''
        if self.mode_type:
            mode = self.mode_type.table_name

        hub = ''
        if self.hub_type:
            hub = self.hub_type.table_name

        return '{} ({} -- {} -- incoming - {})'.format(self.task_name.encode('utf8', 'ignore'), hub,
                                                       mode, self.is_incoming)

    def get_penalty_set(self):
        return self.penalty_set.all()


###################################################################################################


class Task(TaskBaseModel):
    STAKEHOLDER_TYPE_SHIPPING_LINE = 'Forwarder'
    STAKEHOLDER_TYPE_SHIPPER = 'client'
    STAKEHOLDER_TYPE_TRUCKER = 'Trucker'

    is_active = models.BooleanField(default=False)
    task_for = models.ForeignKey(Stakeholder, on_delete=models.CASCADE, blank=True, null=True)

    triggered_at = models.DateTimeField(blank=True, null=True)
    expiry = models.IntegerField(default=5000)
    escalation = models.IntegerField(default=4500)
    estimated_completion = models.IntegerField(default=4000)

    completed_at = models.DateTimeField(blank=True, null=True)

    partially_completed_at = models.DateTimeField(blank=True, null=True)

    escalated_at = models.DateTimeField(blank=True, null=True)
    expired_at = models.DateTimeField(blank=True, null=True)

    notify_stakeholders = models.ManyToManyField(Stakeholder, related_name='notify_stakeholder_task', blank=True,
                                                 null=True)
    secondary_stakeholders = models.ManyToManyField(Stakeholder, related_name='secondary_stakeholder_task', blank=True,
                                                    null=True)

    notification_msg_short = models.CharField(max_length=120)
    notification_msg_long = models.TextField()
    notification_msg_title = models.CharField(max_length=120)

    booking = models.ForeignKey('booking.CPBooking', blank=True, null=True)
    event = models.ForeignKey(Events, blank=True, null=True)
    trigger_tasks_on_completion = models.ManyToManyField('task.Task', related_name='task_triggered_by_task', blank=True,
                                                         null=True)
    dependency_tasks = models.ManyToManyField('task.Task', blank=True, null=True)

    abstract_task = models.ForeignKey(AbstractTask, blank=True, null=True)

    leg = models.ForeignKey('quote.Leg', blank=True, null=True)
    order_number = models.IntegerField(default=0)

    def __str__(self):
        if self.task_name is not None:
            return '{}'.format(self.task_name.encode('utf8', 'ignore'))

    def create_blockchain(self, shipment):
        try:
            container_no = shipment.container_num
            owner = self.task_for.id
            timestamp = time.time()
            quote = shipment.shipper_quote
            extra = {
                "quote_id": quote.quote_number
            }
            create_new_transaction(container_no, owner, timestamp, extra)
        except:
            pass

    def make_quote_leg_active(self):
        # mode_type = self.abstract_task.mode_type
        # hub_type = self.abstract_task.hub_type
        # is_incoming = self.abstract_task.is_incoming
        #
        # if not is_incoming:
        #     leg = Leg.objects.get(
        #         fromHub__dynamic_table=hub_type,
        #         mode__dynamic_table=mode_type
        #     )
        # else:
        #     leg = Leg.objects.get(
        #         toHub__dynamic_table=hub_type,
        #         mode__dynamic_table=mode_type
        #     )
        #
        # if not leg.is_active:
        #     leg.is_active = True
        #     leg.save()
        try:
            leg = self.leg
            if not leg.is_active:
                leg.is_active = True
                leg.save()
        except:
            pass

    def make_quote_leg_inactive(self):
        # mode_type = self.abstract_task.mode_type
        # hub_type = self.abstract_task.hub_type
        # is_incoming = self.abstract_task.is_incoming
        #
        # if not is_incoming:
        #     leg = Leg.objects.get(
        #         fromHub__dynamic_table=hub_type,
        #         mode__dynamic_table=mode_type
        #     )
        # else:
        #     leg = Leg.objects.get(
        #         toHub__dynamic_table=hub_type,
        #         mode__dynamic_table=mode_type
        #     )

        # if not leg.is_active:
        #     leg.is_active = False
        #     leg.save()

        # if not is_incoming:
        #     leg_other_part = {
        #         "other_mode_type": mode_type,
        #         "other_hub_type": leg.toHub.dynamic_table,
        #         "is_incoming": True
        #     }
        # else:
        #     leg_other_part = {
        #         "other_mode_type": mode_type,
        #         "other_hub_type": leg.fromHub.dynamic_table,
        #         "is_incoming": False
        #     }
        try:
            leg = self.leg
            cpbooking = self.booking

            tasks = Task.objects.filter(leg=leg, booking=cpbooking)
            all_leg_tasks_completed = True
            for task in tasks:
                if task.completed_at:
                    all_leg_tasks_completed = False

            if all_leg_tasks_completed:
                leg.is_active = False
                leg.save()
        except:
            pass

    def make_booking_active(self):
        # shipment_booking = ShipmentBooking.objects.get(shipment=shipment)
        # booking = shipment_booking.vendor_booking
        #
        # if not booking.is_active:
        #     booking.is_active = True
        #     booking.save()
        try:
            quote = self.booking.quote
            leg = self.leg
            bookings = ContentType.objects.get(model='booking').model_class().objects.filter(quote=quote, legs=leg)
            for booking in bookings:
                if not booking.is_active:
                    booking.is_active = True
                    booking.save()
        except:
            pass

    def make_booking_inactive(self, shipment):
        try:
            shipment_booking = ShipmentBooking.objects.get(shipment=shipment)
            booking = shipment_booking.vendor_booking
            booking_legs = booking.legs.all()
            cpbooking = self.booking
            tasks = Task.objects.filter(booking=cpbooking, leg__in=booking_legs)
            booking_shipments = ShipmentBooking.objects.filter(vendor_booking=booking)
            b_shipments = []
            for i in booking_shipments:
                b_shipments.append(i.shipment)

            booking_tasks_completed = True
            for task in tasks:
                if not task.get_task_booking_is_filled(booking, b_shipments):
                    booking_tasks_completed = False
                    break

            if booking_tasks_completed:
                booking.is_active = False
                booking.save()
        except:
            pass

    def get_task_booking_is_filled(self, booking, b_shipments):

        if self.task_category == Task.TASK_CATEGORY_FINAL:
            return False

        form = self.form
        form_elements = form.get_elements()
        required_count = 0
        form_element_r_list = []
        for form_element in form_elements:
            required = form_element.get_kwarg('required')
            if required:
                required_count += 1
                form_element_r_list.append(form_element)

        is_filled_count = 0
        # for i in range(1, (self.booking.quote.no_of_containers + 1)):
        #     shipment_num = i
        #
        #     # for form_element in form_element_r_list:
        #     is_filled = FormElementValue.objects.filter(
        #         shipment__shipment_num=shipment_num,
        #         # form_element__form=form,
        #         form_element__in=form_element_r_list,
        #         shipment__shipper_quote=self.booking.quote
        #     ).count() >= required_count
        #     if is_filled:
        #         is_filled_count += 1
        #
        # if task_for_vendor:
        #     if is_filled_count == task_vendor_booking.num_assets:
        #         self.task.mark_as_completed()
        for shipment in b_shipments:
            is_filled = FormElementValue.objects.filter(
                shipment=shipment,
                form_element__in=form_element_r_list,
                task=self
            ).count() >= required_count
            if is_filled:
                is_filled_count += 1

        if is_filled_count == booking.num_assets:
            return True
        else:
            return False

    def get_task_is_filled_percent(self):

        if self.form:
            form = self.form
            form_elements = form.get_elements()
            required_count = 0
            form_element_r_list = []
            for form_element in form_elements:
                required = form_element.get_kwarg('required')
                if required:
                    required_count += 1
                    form_element_r_list.append(form_element)

            is_filled_count = 0
            for i in range(1, (self.booking.quote.no_of_containers + 1)):
                shipment_num = i

                # for form_element in form_element_r_list:
                is_filled = FormElementValue.objects.filter(
                    shipment__shipment_num=shipment_num,
                    # form_element__form=form,
                    form_element__in=form_element_r_list,
                    shipment__shipper_quote=self.booking.quote,
                    task=self
                ).count() >= required_count
                if is_filled:
                    is_filled_count += 1
            total_containers = self.booking.quote.no_of_containers
            task_completed_percentage = round(((float(is_filled_count) / total_containers) * 100))
            # task.completed_percentage = task_completed_percentage
            return task_completed_percentage
        else:
            if self.completed_at:
                return 100
            else:
                return 0

    def mark_as_partially_completed(self):

        if self.trigger_tasks_on == Task.TASK_TRIGGER_PARTIALLY_COMPLETED:

            if not self.partially_completed_at:
                self.partially_completed_at = timezone.now()
                self.save()
                for task in self.trigger_tasks_on_completion.all():
                    task.trigger_task()

            else:
                pass

    def mark_as_completed(self):
        # if self.trigger_tasks_on == Task.TASK_TRIGGER_COMPLETED:
        #     self.completed_at = timezone.now()
        #     self.is_active = False
        #
        #     try:
        #         self.make_quote_leg_inactive()
        #     except:
        #         pass
        #     # self.make_booking_inactive()

        self.completed_at = timezone.now()
        self.is_active = False

        try:
            self.make_quote_leg_inactive()
        except:
            pass

        if self.trigger_tasks_on == Task.TASK_TRIGGER_PARTIALLY_COMPLETED:
            self.partially_completed_at = timezone.now()

        if self.trigger_tasks_on == Task.TASK_TRIGGER_ESCALATED:
            self.escalated_at = timezone.now()

        if self.trigger_tasks_on == Task.TASK_TRIGGER_EXPIRED:
            self.expired_at = timezone.now()

        # if self.task_category == Task.TASK_CATEGORY_FINAL:
        #     try:
        #         self.booking.finish_booking()
        #         self.booking.quickbooks_final()
        #     except:
        #         pass

        try:
            for stakeholder in self.notify_stakeholders.all():
                task_for = self.task_for.user.name
                Notification.objects.create(
                    title="{} Completed".format(self.task_name),
                    description="Task Update: {} completed by {}".format(self.task_name, self.task_for.user.name),
                    stakeholder=stakeholder,
                )
        except:
            pass

        self.save()

        for task in self.trigger_tasks_on_completion.all():
            task.trigger_task()

        # if not self.booking.task_set.filter(Q(completed_at__isnull=True) | Q(is_active=True)).exists():
        #     self.booking.finish_booking()
        else:
            pass

    def trigger_task(self):
        # for task in self.dependency_tasks.all():
        #     if task.is_active:
        #         return False

        if self.completed_at:
            return False

        for task in self.dependency_tasks.all():
            if task.trigger_tasks_on == Task.TASK_TRIGGER_COMPLETED and task.is_active:
                return False
            elif task.trigger_tasks_on == Task.TASK_TRIGGER_PARTIALLY_COMPLETED and not task.partially_completed_at:
                return False
            elif task.trigger_tasks_on == Task.TASK_TRIGGER_ESCALATED and not task.escalated_at:
                return False
            elif task.trigger_tasks_on == Task.TASK_TRIGGER_EXPIRED and not task.expired_at:
                return False

        self.triggered_at = timezone.now()
        self.is_active = True
        self.save()

        try:
            if self.task_category == Task.TASK_CATEGORY_NORMAL:
                self.make_quote_leg_active()
                self.make_booking_active()
                # elif self.task_category == Task.TASK_CATEGORY_FINAL:
                #     task_cpbooking = self.booking
                #     task_cpbooking.finish_booking()
                #     task_cpbooking.quickbooks_final()
        except:
            pass

        return True

    def get_form_data_instance(self, shipment_num):
        fd = FormData(
            task=self,
            shipment_num=shipment_num
        )
        return fd

    def get_form_element_by_name(self, name):
        return self.form.formelement_set.get(name=name)

    def send_notification(self):
        for stakeholder in self.notify_stakeholders.all():
            Notification.objects.create(
                title=self.notification_msg_title,
                message_long=self.notification_msg_long,
                message_short=self.notification_msg_short,
                stakeholder=stakeholder
            )

    def get_variables(self):
        return TaskVariable.objects.filter(cp_booking=self.booking)

    def get_total_shipment(self):
        return self.leg.quote.no_of_containers

    def get_shipment_is_filled(self):
        form = self.form
        # TaskDataOptionsRetreiveView.retrieve()

    def get_escalation_datetime(self):
        if self.triggered_at:
            return self.triggered_at + timezone.timedelta(minutes=self.escalation)
        return None

    def get_expiry_datetime(self):
        if self.triggered_at:
            return self.triggered_at + timezone.timedelta(minutes=self.expiry)
        return None

    def is_task_for_vendor(self):
        return self.task_for.dynamic_table.table_name in [Task.STAKEHOLDER_TYPE_SHIPPING_LINE,
                                                          Task.STAKEHOLDER_TYPE_TRUCKER]


class Form(DateBaseModel):
    name = models.CharField(max_length=50)
    description = models.TextField()

    def get_elements(self):
        return self.formelement_set.all()

    def __str__(self):
        return self.name.encode('utf8', 'ignore')


class FormElement(DateBaseModel):
    '''
    self.kwargs => all the constraints on the field

    currently handling:
        mandatory_properties:
            'required': boolean,

        optional_properties:
            'max_length': if type is one of text
            'choices': json array of *choice_object*  -  if type is choice
            'file_type': a *file_type* object  -  if type is file

        potential_properties:
            'validators': a list of *validator_name*

    glossary:
        'validator_name': should have a corresponding a staticmethod named validate_<validator_name>
        'choice_object: {'<value>': '<display_name>'}
        'file_type': {'<value>': '<display_name>'}
            where pairs are one of:
                 0 - PDF
                 1 - CSV
                 2 - Image
    '''
    TYPE_CHOICE_TEXT = 0
    TYPE_CHOICE_DECIMAL = 1
    TYPE_CHOICE_CHOICE = 2
    TYPE_CHOICE_LAT_LNG = 3
    TYPE_CHOICE_FILE = 4
    TYPE_CHOICE_CHECKBOX = 5
    TYPE_CHOICE_DATETIME = 6
    TYPE_CHOICE_INTEGER = 7

    TYPE_CHOICES = (
        (TYPE_CHOICE_TEXT, 'string'),
        (TYPE_CHOICE_DECIMAL, 'decimal'),
        (TYPE_CHOICE_CHOICE, 'choice'),
        (TYPE_CHOICE_LAT_LNG, 'location'),
        (TYPE_CHOICE_FILE, 'file_upload'),  # @TODO: add validator
        (TYPE_CHOICE_CHECKBOX, 'boolean'),
        (TYPE_CHOICE_DATETIME, 'datetime'),
        (TYPE_CHOICE_INTEGER, 'integer')
    )

    KWARG_DEFAULTS = {
        'required': False,
        'choices': [],
        'max_length': 32,
        'max_value': sys.maxint,
        'min_value': -sys.maxint - 1,
        'validators': [],
        'max_digits': 22,
        'decimal_places': 18
    }

    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_CHOICE_TEXT)
    css_class = models.CharField(max_length=50, default='')
    label = models.CharField(max_length=70)
    placeholder = models.CharField(max_length=70, default='', blank=True, null=True)
    name = models.CharField(max_length=70)
    kwargs = models.TextField(blank=True, null=True)
    # required = models.BooleanField(default=False)
    # choices = models.TextField(blank=True)
    # file_type = models.CommaSeparatedIntegerField(choices=FILE_TYPE_CHOICES, max_length=1024, null=True, blank=True)
    form = models.ForeignKey(Form)
    default = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    assign_to_var = models.CharField(max_length=32, blank=True, null=True)
    is_autofill = models.BooleanField(default=True)

    def __str__(self):
        return self.label.encode('utf8', 'ignore')

    # is_editable = models.BooleanField(default=True)

    # assign_to_variable = models.ForeignKey(TaskVariable)

    def get_default_value(self, shipment_num, task):
        val = TaskVariable.replace_with_variable_value(
            text=self.default,
            cp_booking=task.booking,
            shipment_num=shipment_num,
            task=task
        )
        return None if val == '' else val

    def get_choice_list(self):
        k = self.get_kwarg('choices')
        return k

        # return [(key, value) for key, value in self.get_kwarg('choices').iteritems()]

    def get_kwargs_dict(self):
        if self.kwargs:
            return json.loads(self.kwargs)

        return FormElement.KWARG_DEFAULTS

    def get_kwarg(self, key):
        try:
            return json.loads(self.kwargs)[key]
        except Exception as exc:
            if key in FormElement.KWARG_DEFAULTS:
                return FormElement.KWARG_DEFAULTS[key]

            my_exc = Exception()
            if isinstance(exc, ValueError):
                my_exc.message = 'No kwargs in form_element'
            if isinstance(exc, IndexError):
                my_exc.message = 'No such key in kwargs'
            raise my_exc

    def get_validators(self):
        result = []

        validators = self.get_kwarg('validators')

        for validator in validators:
            validator_method = getattr(FormElement, "validate_{}".format(validator), None)
            if validator_method:
                result.append(validator_method)

        default_validator = getattr(FormElement, "validate_{}".format(self.get_type_display()), None)
        if default_validator:
            result.append(default_validator)

        return result

    @staticmethod
    def validate_container_number(value):
        first10 = value[0:-1]
        check = value[-1]
        char2num = {
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17,
            'H': 18, 'I': 19, 'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26,
            'P': 27, 'Q': 28, 'R': 29, 'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35,
            'X': 36, 'Y': 37, 'Z': 38,
        }
        total = sum(char2num[c] * 2 ** x for x, c in enumerate(first10))
        if not ((total % 11) % 10 == char2num[check]):
            raise ValidationError('Not a valid container number')

    # This is how a validator method should look like
    @staticmethod
    def validate_location(value):
        try:
            lat_lng = json.loads(value)

            if len(lat_lng) != 2:
                raise ValidationError('Json list should have exactly 2 floats')

            if type(lat_lng[0]) is not float or type(lat_lng[1]) is not float:
                raise ValidationError('Json list should have exactly 2 floats')

        except ValueError:
            raise ValidationError('Not a json list')

    @staticmethod
    def validate_unique_value(value):
        pass


# def index_validator():
#     if not TaskVariable.is_indiced and TaskVariable.index:
#         raise ValidationError('is_indiced set is to false')

def task_upload_file_location(instance, filename):
    return 'task_docs/{}/{}'.format(str(instance.id), filename)


class FileFormElementValue(DateBaseModel):
    form_element_value = models.OneToOneField('task.FormElementValue', blank=True, null=True)
    doc = models.FileField(blank=True, null=True, upload_to=task_upload_file_location)


class FormElementValue(DateBaseModel):
    value = models.TextField(blank=True, null=True)
    shipment = models.ForeignKey('shipment.Shipment')
    form_element = models.ForeignKey(FormElement)
    task = models.ForeignKey('task.Task')

    def __str__(self):
        return self.value.encode('utf8', 'ignore')

    class Meta:
        unique_together = ('shipment', 'form_element', 'task')

    def get_type_casted_value(self, task):
        type = self.form_element.get_type_display()
        raw_value = getattr(self, 'get_value_{}'.format(type))

        return TaskVariable.replace_with_variable_value(
            text=raw_value,
            cp_booking=self.shipment.shipper_quote.cpbooking,
            shipment_num=self.shipment.shipment_num,
            task=task
        )

    @property
    def get_value_choice(self):
        return self.value

    @property
    def get_value_string(self):
        return self.value

    @property
    def get_value_decimal(self):
        return self.value

    @property
    def get_value_location(self):
        lat_lng = json.loads(self.value)
        return float(lat_lng[0]), float(lat_lng[1])

    @property
    def get_value_file_upload(self):
        return self.fileformelementvalue.doc

    @property
    def get_value_boolean(self):
        return bool(self.value)

    @property
    def get_value_datetime(self):
        return dateutil.parser.parse(self.value)

    @property
    def get_value_integer(self):
        return int(self.value)


class TaskVariable(DateBaseModel):
    TYPE_INDEX_NONE = 0
    TYPE_INDEX_VENDOR = 1
    TYPE_INDEX_ALL = 2

    TYPE_INDEX_CHOICES = (
        (TYPE_INDEX_NONE, 'none'),
        (TYPE_INDEX_VENDOR, 'vendor'),
        (TYPE_INDEX_ALL, 'all')
    )

    name = models.CharField(max_length=120)
    display_name = models.CharField(max_length=120)
    index_type = models.IntegerField(choices=TYPE_INDEX_CHOICES, default=TYPE_INDEX_NONE)
    value = models.CharField(max_length=1024, blank=True, null=True)
    index = models.IntegerField(default=0)
    cp_booking = models.ForeignKey('booking.CPBooking')

    def __str__(self):
        return self.name.encode('utf8', 'ignore')

    @staticmethod
    def variable_to_value(variable_name, cp_booking, shipment_num, task):
        form = task.form

        qs = TaskVariable.objects.filter(
            cp_booking=cp_booking,
            name=variable_name.replace('[i]', '').replace('[v]', '')
        )

        if '[i]' in variable_name:
            try:
                return qs.get(index_type=TaskVariable.TYPE_INDEX_ALL, index=shipment_num).value
            except TaskVariable.DoesNotExist:
                qs = qs.filter(index_type=TaskVariable.TYPE_INDEX_ALL).order_by('-created_at')
                if qs.count() > 0:
                    return qs.first().value
                else:
                    return ""
        elif '[v]' in variable_name:
            try:
                booking = task.leg.leg_booking.get(shipmentbooking__shipment__shipment_num=shipment_num)
                v = qs.get(index_type=TaskVariable.TYPE_INDEX_VENDOR, index=booking.booking_index).value
                return v
            except TaskVariable.DoesNotExist:
                return ""
        else:
            try:
                return qs.get(index_type=TaskVariable.TYPE_INDEX_NONE).value
            except TaskVariable.DoesNotExist:
                return ""

    @staticmethod
    def replace_with_variable_value(text, cp_booking, shipment_num, task):
        matches = re.findall('<%(.*?)%>', str(text), re.DOTALL)
        for var in matches:
            value = TaskVariable.variable_to_value(
                variable_name=var,
                cp_booking=cp_booking,
                shipment_num=shipment_num,
                task=task
            )
            text = text.replace(
                "<%{}%>".format(var),
                value
            )
        return text


class TaskAcknowledgement(DateBaseModel):
    name = models.CharField(max_length=64)
    shipment = models.ForeignKey('shipment.Shipment')
    description = models.CharField(max_length=1024)

    def __str__(self):
        return self.name.encode('utf8', 'ignore')


class TaskFormData(DateBaseModel):
    task = models.ForeignKey(Task)
    shipment = models.ForeignKey('shipment.Shipment')
    data = models.TextField()

    def __str__(self):
        return self.task.task_name


class FileUploads(DateBaseModel):
    file_number = models.PositiveIntegerField()
    shipment = models.ForeignKey('shipment.Shipment')
    file = models.FileField()

    def __str__(self):
        return self.file_number


class TaskFiles(DateBaseModel):
    files = models.ManyToManyField(FileUploads)
    shipment = models.ForeignKey('shipment.Shipment')
    task = models.ForeignKey(Task)

    def __str__(self):
        return self.task.task_name
