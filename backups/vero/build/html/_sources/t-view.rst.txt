task.views
-----------------------

.. automodule:: task.views
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.http.response import Http404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from booking.models import Booking
from shipment.models import ShipmentBooking, Shipment
from task import serializer
from task.models import Task, AbstractTask, FormElement, Form, FormElementValue, TaskVariable
from task.serializer import TaskSerializer, AbstractTaskSerializer, FormElementsSerializer, FormSerializer, \
    TaskDataSerializer, TaskVariableSerializerModel, FormRetrieveSerializer, AbstractTaskWithPenaltiesSerializer, \
    TaskGantChartSerializer
from utils.metadata import CPMeta
from utils.pagination import CamelportPagination


class AbstractTaskWithPenaltiesListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AbstractTaskWithPenaltiesSerializer

    def get_queryset(self):
        return AbstractTask.objects.all()


class TasksForBookingListView(generics.ListAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            booking_id=self.kwargs['booking_id']
        ).order_by('created_at')


class TaskLCAPIView(generics.CreateAPIView):
    def __init__(self, **kwargs):
        super(TaskLCAPIView, self).__init__(**kwargs)
        self.cache_task = None

    def get_serializer_class(self):
        if self.cache_task is None:
            self.cache_task = Task.objects.get(pk=self.kwargs['task_id'])
        if self.cache_task.task_type is Task.TASK_TYPE_ACKNOWLEDGEMENT:
            return serializer.AcknowledgementSerializer
        elif self.cache_task.task_type is Task.TASK_TYPE_ACK:
            return serializer.TaskDataLCSerializer
        elif self.cache_task.task_type is Task.TASK_TYPE_FILE_UPLOAD:
            return serializer.TaskFileUploadSerializer
        elif self.cache_task.task_type is Task.TASK_TYPE_DOWNLOAD:
            return serializer.TaskFileDownloadSerializer

    def get_serializer_context(self):
        context = super(TaskLCAPIView, self).get_serializer_context()
        if self.cache_task is None:
            self.cache_task = Task.objects.get(pk=self.kwargs['task_id'])
        context['task'] = self.cache_task
        return context


class TaskCompletedApiView(generics.ListAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            (
                Q(task_for=self.request.user.stakeholder) |
                Q(secondary_stakeholders=self.request.user.stakeholder)
            ) &
            Q(completed_at__isnull=False)
        ).order_by('created_at')


class TaskListCreateAPIView(generics.ListCreateAPIView):
    """get: Return a list of all the existing Task.,
       post:Create new task"""
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            (
                Q(task_for=self.request.user.stakeholder) |
                Q(secondary_stakeholders=self.request.user.stakeholder)
            ) &
            Q(completed_at__isnull=True)
        ).order_by('created_at')


class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all()


class ActiveApiView(generics.ListAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = TaskSerializer

    def get_queryset(self):
        query = """
        SELECT
            * ,
            add_minutes("task_task"."triggered_at", "task_task"."expiry") AS "escalation_timestamp"
        FROM "task_task"
        LEFT OUTER JOIN
          "task_task_secondary_stakeholders" ON ("task_task"."id" = "task_task_secondary_stakeholders"."task_id")
        WHERE
          (
            (
              "task_task"."task_for_id" = '{stakeholder_id}' OR
              "task_task_secondary_stakeholders"."stakeholder_id" = '{stakeholder_id}'
            ) AND
            "task_task"."completed_at" IS NULL AND
            "task_task"."triggered_at" IS NOT NULL AND
            "task_task"."expired_at" IS NULL
          )
        ORDER BY "escalation_timestamp" ASC
        """.format(stakeholder_id=self.request.user.stakeholder.id)
        return list(Task.objects.raw(str(query)))


###########################################################################################
class AllTaskCPBookingApiView(generics.ListAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = TaskGantChartSerializer

    def get_queryset(self):
        cpbooking = self.kwargs['cpbooking_id']
        tasks = Task.objects.filter(booking_id=cpbooking).order_by('order_number').distinct()
        return tasks


class AllTaskBookingApiView(generics.ListAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = TaskGantChartSerializer

    def get_queryset(self):
        booking = Booking.objects.get(id=self.kwargs['booking_id'])
        cpbooking = booking.quote.cpbooking
        tasks = Task.objects.filter(booking=cpbooking).order_by('order_number').distinct()
        return tasks


#########################################################################################


class AbstractTaskListCreateAPIView(generics.ListCreateAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = AbstractTaskSerializer

    def get_queryset(self):
        return AbstractTask.objects.all()


# class AbstractTaskWithFormLCAPIView(generics.CreateAPIView):
#     def __init__(self, **kwargs):
#         super(AbstractTaskWithFormLCAPIView, self).__init__(**kwargs)
#         self.cache_task = None
#
#     def get_serializer_class(self):
#         if self.cache_task is None:
#             self.cache_task = Task.objects.get(pk=self.kwargs['task_id'])
#         if self.cache_task.task_type is Task.TASK_TYPE_ACKNOWLEDGEMENT:
#             return serializer.AcknowledgementSerializer
#         elif self.cache_task.task_type is Task.TASK_TYPE_DATA_INPUT:
#             return serializer.TaskDataLCSerializer
#         elif self.cache_task.task_type is Task.TASK_TYPE_FILE_UPLOAD:
#             return serializer.TaskFileUploadSerializer
#         elif self.cache_task.task_type is Task.TASK_TYPE_DOWNLOAD:
#             return serializer.TaskFileDownloadSerializer
#
#     def get_serializer_context(self):
#         context = super(TaskLCAPIView, self).get_serializer_context()
#         if self.cache_task is None:
#             self.cache_task = Task.objects.get(pk=self.kwargs['task_id'])
#         context['task'] = self.cache_task
#         return context


class AbstractTaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AbstractTaskSerializer

    def get_queryset(self):
        return AbstractTask.objects.all()

    def get_serializer(self, *args, **kwargs):
        return super(AbstractTaskRetrieveUpdateDestroyAPIView, self).get_serializer(*args, **kwargs)


class FormElementsLCView(generics.ListCreateAPIView):
    serializer_class = FormElementsSerializer
    queryset = FormElement.objects.all()


class FormElementsRUDView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FormElementsSerializer
    queryset = FormElement.objects.all()


class TaskDataOptionsRetreiveView(generics.RetrieveAPIView):
    def __init__(self, **kwargs):
        super(TaskDataOptionsRetreiveView, self).__init__(**kwargs)
        self.task = None

    permission_classes = [IsAuthenticated]

    def get_object(self):
        self.task = Task.objects.get(pk=self.kwargs['pk'])
        f_obj = self.task.form
        return f_obj

    def get_queryset(self):
        form_obj = Form.objects.filter(
            Q(task__task_for=self.request.user.stakeholder) |
            Q(task__secondary_stakeholders=self.request.user.stakeholder)
        )
        return form_obj

    # def get_serializer(self, *args, **kwargs):
    #     return FormSerializer

    # serializer_class = FormSerializer

    def get_serializer_class(self):
        return FormSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        result = serializer.data

        task_serializer = TaskVariableSerializerModel(
            var_names=['container_nums'],  # <--
            cp_booking_id=self.task.booking_id,
            stakeholder=request.user.stakeholder
        )

        vars = task_serializer.data()

        titles = vars.setdefault(
            'container_nums',
            {
                'values': self.get_default_container_values()
            }
        )

        result['shipment_details'] = self._get_is_filled(titles['values'])

        v = vars

        return Response(result)

    def get_default_container_values(self):
        default_cont_values = []
        request_stakeholder = self.request.user.stakeholder
        # request_stakeholder = self.context['request'].user.stakeholder

        task_for_vendor = False
        if self.task.task_for == request_stakeholder:
            if settings.STAKEHOLDER_TYPE[
                request_stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:
                task_vendor_booking = Booking.objects.get(service_provider=request_stakeholder,
                                                          quote=self.task.booking.quote)
                sb = ShipmentBooking.objects.filter(vendor_booking=task_vendor_booking)
                j = []
                for k in sb:
                    j.append({
                        'i': k.shipment.shipment_num,
                        'container_num': k.shipment.container_num
                    })
                task_vendor_booking_shipment_num_list = j
                task_for_vendor = True

        if task_for_vendor:
            container_num = 1
            for i in task_vendor_booking_shipment_num_list:
                default_cont_values.append({
                    'shipment_num': i['i'],
                    'value': i['container_num'] or "Container #{}".format(container_num)
                })
                container_num += 1
        else:

            shipment_values = Shipment.objects.filter(shipper_quote=self.task.booking.quote).distinct().values_list(
                'shipment_num', 'container_num')

            shipment_values = {x[0]: x[1] for x in shipment_values}

            for i in range(self.task.booking.quote.no_of_containers):
                default_cont_values.append({
                    'shipment_num': i + 1,
                    'value': shipment_values[i + 1] or "Container #{}".format(i + 1)
                })

        # for i in range(self.task.booking.quote.no_of_containers):
        #     default_cont_values.append({
        #         'shipment_num': i + 1,
        #         'value': "Container #{}".format(i + 1)
        #     })

        return default_cont_values

    def _get_is_filled(self, vars):
        # for var in vars:
        #     var['is_filled'] = FormElementValue.objects.filter(
        #         shipment__shipment_num=var['shipment_num'],
        #         form_element__form=self.task.form,
        #         shipment__shipper_quote=self.task.booking.quote
        #     ).count() > 0
        #
        #     var['title'] = var.pop('value')

        #######################################################################

        form = self.task.form
        form_elements = form.get_elements()
        required_count = 0
        form_element_r_list = []
        for form_element in form_elements:
            required = form_element.get_kwarg('required')
            if required:
                required_count += 1
                form_element_r_list.append(form_element)

        for var in vars:
            var['is_filled'] = FormElementValue.objects.filter(
                shipment__shipment_num=var['shipment_num'],
                # form_element__form=form,
                form_element__in=form_element_r_list,
                shipment__shipper_quote=self.task.booking.quote,
                task=self.task
            ).count() >= required_count

            check_is_filled = var['is_filled']

            var['title'] = var.pop('value')

        #######################################################################


        return vars


class FormElementValueCView(generics.CreateAPIView):
    def __init__(self, **kwargs):
        super(FormElementValueCView, self).__init__(**kwargs)
        self.task = None

    serializer_class = TaskDataSerializer
    queryset = Task.objects.filter(
        form__isnull=False
    )

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        if self.task:
            kwargs['task'] = self.task
        else:
            kwargs['task'] = self.task = self.get_queryset().get(
                pk=self.kwargs['pk']
            )
        kwargs['shipment_num'] = self.kwargs['s_num']
        kwargs['is_create'] = True
        return serializer_class(*args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        result = serializer.data

        values = []

        for key, value in result.items():
            values.append({
                'name': key,
                'label': serializer.field_form_element[key].label,
                'type': serializer.field_form_element[key].get_type_display(),
                'value': value
            }
            )

        final_result = {
            'is_completed': not self.task.is_active,
            'data': values
        }

        return Response(final_result, status=status.HTTP_201_CREATED, headers=headers)


class FormElementValueRUDView(generics.RetrieveUpdateDestroyAPIView):
    def __init__(self, **kwargs):
        super(FormElementValueRUDView, self).__init__(**kwargs)
        self.task = None

    serializer_class = TaskDataSerializer

    def get_queryset(self):
        t = Task.objects.filter(
            form__isnull=False,
            triggered_at__isnull=False
        ).filter(
            Q(
                notify_stakeholders=self.request.user.stakeholder
            ) |
            Q(
                task_for=self.request.user.stakeholder
            ) |
            Q(
                secondary_stakeholders=self.request.user.stakeholder
            )
        )
        return t

    def get_object(self):
        self.task = self.get_queryset().distinct().get(pk=self.kwargs['pk'])
        result = self.task.get_form_data_instance(self.kwargs['s_num'])
        if len(result.form_elements_values) == 0:
            raise Http404
        return result

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        if self.task:
            kwargs['task'] = self.task
        else:
            kwargs['task'] = self.get_queryset().distinct().get(
                pk=self.kwargs['pk']
            )
        kwargs['shipment_num'] = self.kwargs['s_num']
        kwargs['instance'] = args[0]
        return serializer_class(**kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        result = serializer.data

        values = []

        for key, value in result.items():
            values.append({
                'name': key,
                'label': serializer.field_form_element[key].label,
                'type': serializer.field_form_element[key].get_type_display(),
                'value': value
            }
            )

        final_result = {
            'is_completed': not self.task.is_active,
            'data': values
        }

        return Response(final_result)


class FormRetrieveView(generics.RetrieveAPIView):
    serializer_class = FormRetrieveSerializer

    def __init__(self, **kwargs):
        super(FormRetrieveView, self).__init__(**kwargs)
        self.task = None

    def get_queryset(self):
        task = Task.objects.filter(
            form__isnull=False,
            triggered_at__isnull=False
        ).filter(
            Q(
                notify_stakeholders=self.request.user.stakeholder
            ) |
            Q(
                task_for=self.request.user.stakeholder
            ) |
            Q(
                secondary_stakeholders=self.request.user.stakeholder
            )
        )
        return task

    def get_object(self):
        self.task = self.get_queryset().distinct().get(pk=self.kwargs['pk'])
        return self.task.form

    def get_serializer_context(self):
        context = super(FormRetrieveView, self).get_serializer_context()
        context['task'] = self.task
        context['s_num'] = self.kwargs['s_num']
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        result = serializer.data

        # task_serializer = TaskVariableSerializerModel(
        #     var_names=['container_nums'],  # <--
        #     cp_booking_id=self.task.booking_id,
        #     stakeholder=request.user.stakeholder
        # )
        #
        # vars = task_serializer.data()
        #
        # titles = vars.setdefault(
        #     'container_nums',
        #     {
        #         'values': self.get_default_container_values()
        #     }
        # )
        #
        # result['shipment_details'] = self._get_is_filled(titles['values'])
        #
        # v = vars
        # result['']
        return Response(result)


class TaskVariableAllRUDView(APIView):
    def get(self, request, *args, **kwargs):

        var_names_set = set()
        var_names_list_all = []
        var_names_list = []
        task_variables_all = TaskVariable.objects.filter(cp_booking_id=kwargs['booking_id'])

        # check_type_vn = type(var_names_all)
        for task_variable in task_variables_all:
            var_names_list_all.append(task_variable.name)
            v = var_names_list_all

        # var_names_set.update(var_names_list_all)

        for var_names in var_names_list_all:
            var_names_set.add(var_names)
            vv = var_names_set

        for var_names in var_names_set:
            var_names_list.append(var_names)

        task_serializer = TaskVariableSerializerModel(
            var_names=var_names_list,
            cp_booking_id=kwargs['booking_id'],
            stakeholder=request.user.stakeholder
        )

        return Response(task_serializer.data())


class TaskVariableRUDView(APIView):
    def get(self, request, *args, **kwargs):
        task_serializer = TaskVariableSerializerModel(
            var_names=self.request.query_params['var_names'].split(','),
            cp_booking_id=kwargs['booking_id'],
            stakeholder=request.user.stakeholder
        )

        return Response(task_serializer.data())


class MarkCompletedView(APIView):
    def get(self, request, *args, **kwargs):

        task_id = kwargs['task_id']

        task = Task.objects.get(pk=task_id)

        try:
            task.mark_as_completed()
            task_completed = True
        except:
            task_completed = False

        tc = task_completed

        return Response(task_completed, status=status.HTTP_200_OK)


class ShipperLogTaskListView(APIView):
    def get_result(self, limit=10, offset=0):
        query = """
            SELECT s.shipment_num, s.container_num, t.id as task_id, t.task_name, max(f.created_at) as updated_at, c.cp_booking_number
            FROM task_formelementvalue f
            INNER JOIN shipment_shipment s
              ON s.id = f.shipment_id
            INNER JOIN quote_quote q
              ON q.id = s.shipper_quote_id
            INNER JOIN booking_cpbooking c
              ON c.quote_id = q.id
            INNER JOIN task_formelement e
              ON e.id = f.form_element_id
            INNER JOIN task_form tf
              ON tf.id = e.form_id
            INNER JOIN task_task t
              ON t.form_id = tf.id AND t.booking_id = c.id
            WHERE
              (
                q.stakeholder_id = '{stakeholder_id}'
              )
            GROUP BY t.id, s.id, c.cp_booking_number
            ORDER BY updated_at DESC
            LIMIT {limit}
            OFFSET {offset}
        """.format(
            limit=limit,
            offset=offset,
            stakeholder_id=self.request.user.stakeholder.id
        )

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                'shipment_num': row[0],
                'container_num': row[1],
                'task_id': row[2],
                'task_name': row[3],
                'updated_at': row[4],
                'booking_num': row[5]
            })

        return result

    def get(self, request, *args, **kwargs):
        page_num = int(request.query_params.get('page', 1))

        offset = (page_num - 1) * 15
        limit = page_num * 15

        return Response(
            self.get_result(
                limit=limit,
                offset=offset
            )
        )


class VendorLogTaskListView(APIView):
    def get_result(self, limit=10, offset=0):
        query = """
            SELECT s.shipment_num, s.container_num, t.id as task_id, t.task_name, max(f.created_at) as updated_at, b.booking_number
            FROM task_formelementvalue f
            INNER JOIN shipment_shipment s
              ON s.id = f.shipment_id
            INNER JOIN quote_quote q
              ON q.id = s.shipper_quote_id
            INNER JOIN booking_cpbooking c
              ON c.quote_id = q.id
            INNER JOIN task_formelement e
              ON e.id = f.form_element_id
            INNER JOIN task_form tf
              ON tf.id = e.form_id
            INNER JOIN task_task t
              ON t.form_id = tf.id AND t.booking_id = c.id
            INNER JOIN booking_booking b
              ON b.quote_id = q.id AND b.service_provider_id = '{stakeholder_id}'
            WHERE
              (
                t.task_for_id = '{stakeholder_id}'
              )
            GROUP BY t.id, s.id, b.booking_number
            ORDER BY updated_at DESC
            LIMIT {limit}
            OFFSET {offset}
        """.format(
            limit=limit,
            offset=offset,
            stakeholder_id=self.request.user.stakeholder.id
        )

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                'shipment_num': row[0],
                'container_num': row[1],
                'task_id': row[2],
                'task_name': row[3],
                'updated_at': row[4],
                'booking_num': row[5]
            })

        return result

    def get(self, request, *args, **kwargs):
        page_num = int(request.query_params.get('page', 1))

        offset = (page_num - 1) * 15
        limit = page_num * 15

        return Response(
            self.get_result(
                limit=limit,
                offset=offset,

            )
        )
