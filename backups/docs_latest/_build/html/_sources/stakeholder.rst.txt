STAKEHOLDER
-----------

views
+++++

.. automodule:: stakeholder.views

**RegisterView**

.. autoclass:: RegisterView
   :members:
   :inherited-members: generics.CreateAPIView
   :show-inheritance:

**Check_Is_EnabledView**

.. autoclass:: Check_Is_EnabledView
   :members:

**LoginView**

.. autoclass:: LoginView
   :members:

**GuestStakeholderView**

.. autoclass:: GuestStakeholderView
   :members:

**GuestStakeholderRUDView**

.. autoclass::  GuestStakeholderRUDView
   :members:
   :inherited-members:

**StakeholderTypeView**

.. autoclass:: StakeholderTypeView
   :members:
   :inherited-members:

**StakeholderRegStatusUpdateView**

.. autoclass:: StakeholderRegStatusUpdateView
   :members:
   :inherited-members:

**StakeholderUpdateView**

.. autoclass:: StakeholderUpdateView
   :members:
   :inherited-members:

**StakeholderRetrieveView**

.. autoclass:: StakeholderRetrieveView
   :members:
   :inherited-members:

**BusinessEntityAutocompleteView**

.. autoclass:: BusinessEntityAutocompleteView
   :members:
   :inherited-members:

**SendOTPView**

.. autoclass:: SendOTPView
   :members:
   :inherited-members:

**SendOTPEwayBillView**

.. autoclass:: SendOTPEwayBillView
   :members:
   :inherited-members:

**VerifyOTPView**

.. autoclass:: VerifyOTPView
   :members:
   :inherited-members:

**RetryOTPView**

.. autoclass:: RetryOTPView
   :members:
   :inherited-members:

**VerifyEmailView**

.. autoclass:: VerifyEmailView
   :members:
   :inherited-members:

**EWayBillGSTView**

.. autoclass:: EWayBillGSTView
   :members:
   :inherited-members:

**inttra_auth_check**

.. autoclass:: inttra_auth_check
   :members:
   :inherited-members:

**itekseal_auth_check**

.. autoclass:: itekseal_auth_check
   :members:
   :inherited-members:

**odex_auth_check**

.. autoclass:: odex_auth_check
   :members:
   :inherited-members:

**GuestStakeholderListView**

.. autoclass:: GuestStakeholderListView
   :members:
   :inherited-members:

**ChangePasswordRequestView**

.. autoclass:: ChangePasswordRequestView
   :members:
   :inherited-members:

**ChangeStakeholderPasswordView**

.. autoclass:: ChangeStakeholderPasswordView
   :members:
   :inherited-members:

**ChangeUserPasswordView**

.. autoclass:: ChangeUserPasswordView
   :members:
   :inherited-members:

**StakeholderInfoRetrieveAPIView**

.. autoclass:: StakeholderInfoRetrieveAPIView
   :members:
   :inherited-members:

**EmailVerifyView**

.. autoclass:: EmailVerifyView
   :members:
   :inherited-members:


models
++++++

.. automodule:: stakeholder.models

.. autoclass:: Stakeholder
   :members:
   :inherited-members:

.. autoclass:: GuestStakeholder
   :members:
   :inherited-members: DateBaseModel

.. autoclass:: BusinessEntity
   :members:
   :inherited-members: DateBaseModel

.. autoclass:: StakeholderInfo
   :members:
   :inherited-members: DateBaseModel

.. autoclass:: Session
   :members:
   :inherited-members: DateBaseModel

.. autoclass:: EmailVerifyToken
   :members:
   :inherited-members: DateBaseModel


serializer
+++++++++++

.. automodule:: stakeholder.serializers

.. autoclass:: StakeholderRegisterSerializer
   :members:
   :inherited-members:


.. autoclass:: StakeholderRegStatusSerializer
   :members:
   :inherited-members:


.. autoclass:: ChildStakeholderSerializer
   :members:
   :inherited-members:

.. autoclass:: GuestStakeholderSerializer
   :members:
   :inherited-members:

.. autoclass:: StakeholderUpdateSerializer
   :members:
   :inherited-members:


.. autoclass:: BusinessEntitySerializer
   :members:
   :inherited-members:

.. autoclass:: ChildStakeholderListSerializer
   :members:
   :inherited-members:

.. autoclass:: StakeholderFullSerializer
   :members:
   :inherited-members:

.. autoclass:: StakeholderShortSerializer
   :members:
   :inherited-members:

.. autoclass:: StakeholderChangePasswordSerializer
   :members:
   :inherited-members:

.. autoclass:: StakeholderInfoSerializer
   :members:
   :inherited-members:

.. autoclass:: StakeholderDetailSerializer
   :members:
   :inherited-members:


























