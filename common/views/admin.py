"""
Admin Views

This module contains all admin-related viewsets for managing:
- Staff (doctors and nurses)
- Patients
- Clinics
- Reports and analytics
- Unified schedule (consultations and appointments)

Only accessible by authenticated administrators.
"""

import logging
import random
import string
from datetime import datetime, timedelta, date
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Q, Count, Sum
from django.db.models.functions import TruncMonth, ExtractYear
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status

from ..models import User, DoctorSpecialization, NurseSpecialization, DoctorProfile, NurseProfile

logger = logging.getLogger(__name__)


class StaffViewSet(ViewSet):
    """
    ViewSet for managing staff (doctors and nurses)
    Only accessible by admins
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/staff/
        List all staff members (doctors and nurses)
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get admin profile to determine clinic access
        admin_profile = None
        try:
            admin_profile = request.user.admin_profile
        except:
            pass

        is_super_admin = admin_profile is None or admin_profile.is_super_admin or (admin_profile and not admin_profile.clinic)
        clinic_id = admin_profile.clinic_id if admin_profile and admin_profile.clinic else None

        # show_deleted=true returns only soft-deleted staff, otherwise only active
        show_deleted = request.query_params.get('show_deleted', 'false').lower() == 'true'

        if is_super_admin:
            # Super admin: see ALL staff (independent + clinic-assigned)
            # Get all doctors and nurses
            doctor_users = User.objects.filter(role='doctor', is_deleted=show_deleted)
            nurse_users = User.objects.filter(role='nurse', is_deleted=show_deleted)
            staff = list(doctor_users) + list(nurse_users)
        else:
            # Clinic admin: see ONLY their clinic's staff
            # Get doctors and nurses from THIS clinic only
            doctor_profiles = DoctorProfile.objects.filter(clinic_id=clinic_id, user__is_deleted=show_deleted).select_related('user')
            nurse_profiles = NurseProfile.objects.filter(clinic_id=clinic_id, user__is_deleted=show_deleted).select_related('user')

            staff = [dp.user for dp in doctor_profiles] + [np.user for np in nurse_profiles]

        # Serialize staff data
        staff_data = []
        for member in staff:
            # Get all specializations and other data from profile models
            specialization = None
            clinic = None
            availability_status = None
            availability_note = None

            if member.role == 'doctor':
                try:
                    profile = member.doctor_profile
                    # Get specializations from profile
                    specs = list(profile.specializations.values_list('name_ru', flat=True))
                    if specs:
                        specialization = ', '.join(specs)
                    elif profile.specialization:
                        specialization = profile.specialization.name_ru
                    clinic = profile.clinic
                    availability_status = profile.availability_status
                    availability_note = profile.availability_note
                except:
                    profile = None

            elif member.role == 'nurse':
                try:
                    profile = member.nurse_profile
                    # Get specializations from profile
                    specs = list(profile.specializations.values_list('name_ru', flat=True))
                    if specs:
                        specialization = ', '.join(specs)
                    elif profile.specialization:
                        specialization = profile.specialization.name_ru
                    clinic = profile.clinic
                    availability_status = profile.availability_status
                    availability_note = profile.availability_note
                except:
                    profile = None

            staff_data.append({
                'id': member.id,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'email': member.email,
                'phone': member.phone,
                'role': member.role,
                'specialization': specialization,
                'gender': member.gender,
                'birth_date': member.birth_date.isoformat() if member.birth_date else '',
                'address': member.address,
                'city': member.city,
                'language': member.language,
                'years_of_experience': profile.years_of_experience if profile else None,
                'offline_consultation_price': str(profile.offline_consultation_price) if profile and profile.offline_consultation_price is not None else None,
                'online_consultation_price': str(profile.online_consultation_price) if profile and profile.online_consultation_price is not None else None,
                'preferred_consultation_duration': profile.preferred_consultation_duration if profile else None,
                'online_work_schedule': profile.online_work_schedule if profile else None,
                'offline_work_schedule': profile.offline_work_schedule if profile else None,
                'is_active': member.is_active,
                'is_deleted': member.is_deleted,
                'availability_status': availability_status,
                'availability_note': availability_note,
                'created_at': member.created_at.isoformat() if member.created_at else None,
                'clinic': {
                    'id': clinic.id,
                    'name': clinic.name
                } if clinic else None
            })

        return Response(staff_data, status=status.HTTP_200_OK)

    def create(self, request):
        """
        POST /api/v1/staff/
        Create a new staff member (doctor or nurse)
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get data from request
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        if phone:
            phone = '+' + ''.join(c for c in phone if c.isdigit())
        password = request.data.get('password')
        role = request.data.get('role')  # 'doctor' or 'nurse'
        specialization = request.data.get('specialization', '')

        # Additional optional fields
        gender = request.data.get('gender')
        birth_date = request.data.get('birth_date')
        address = request.data.get('address')
        city = request.data.get('city')
        language = request.data.get('language')
        years_of_experience = request.data.get('years_of_experience')
        offline_consultation_price = request.data.get('offline_consultation_price')
        online_consultation_price = request.data.get('online_consultation_price')
        preferred_consultation_duration = request.data.get('preferred_consultation_duration')
        online_work_schedule = request.data.get('online_work_schedule')
        offline_work_schedule = request.data.get('offline_work_schedule')

        # Validate required fields
        if not all([first_name, last_name, email, phone, password, role]):
            return Response(
                {'error': 'Все обязательные поля должны быть заполнены'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate role
        if role not in ['doctor', 'nurse']:
            return Response(
                {'error': 'Роль должна быть doctor или nurse'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password length
        if len(password) < 8:
            return Response(
                {'error': 'Пароль должен содержать минимум 8 символов'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Collect all validation errors
        validation_errors = []

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            validation_errors.append('Пользователь с таким email уже существует')

        # Check if phone already exists
        if phone and User.objects.filter(phone=phone).exists():
            validation_errors.append('Пользователь с таким телефоном уже существует')

        # Return all validation errors together
        if validation_errors:
            return Response(
                {'error': '. '.join(validation_errors)},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get admin profile to determine clinic access
            admin_profile = None
            try:
                admin_profile = request.user.admin_profile
            except:
                pass

            is_super_admin = admin_profile is None or admin_profile.is_super_admin or (admin_profile and not admin_profile.clinic)

            # Determine clinic assignment
            if is_super_admin:
                # Super admin: can create independent staff OR assign to any clinic
                clinic_id = request.data.get('clinic_id')  # Optional from request
            else:
                # Clinic admin: must assign to their clinic
                clinic_id = admin_profile.clinic_id

            clinic = None
            if clinic_id:
                from clinics.models import Clinics
                try:
                    clinic = Clinics.objects.get(id=clinic_id)
                except Clinics.DoesNotExist:
                    return Response(
                        {'error': 'Клиника не найдена'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create new staff member (User)
            new_staff = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role=role,
                gender=gender if gender else None,
                birth_date=birth_date if birth_date else None,
                address=address if address else None,
                city=city if city else None,
                language=language if language else 'ru',
                is_active=True,
                is_deleted=False
            )

            # Set password (will be hashed automatically by set_password)
            new_staff.set_password(password)
            new_staff.save()

            # Handle specializations (supports comma-separated multiple specializations)
            specs = []
            if specialization:
                # Split by comma and strip whitespace
                spec_names = [s.strip() for s in specialization.split(',') if s.strip()]

                if role == 'doctor':
                    for spec_name in spec_names:
                        # Try to find existing specialization by name_ru
                        spec = DoctorSpecialization.objects.filter(name_ru=spec_name).first()
                        if not spec:
                            # Create new specialization with unique names
                            try:
                                spec = DoctorSpecialization.objects.create(
                                    name_ru=spec_name,
                                    name_kz=f"{spec_name} (KZ)",
                                    name_en=f"{spec_name} (EN)"
                                )
                            except Exception:
                                # If creation fails, try to find by any name field
                                spec = DoctorSpecialization.objects.filter(
                                    Q(name_ru=spec_name) |
                                    Q(name_kz=spec_name) |
                                    Q(name_en=spec_name)
                                ).first()
                        if spec:
                            specs.append(spec)

                elif role == 'nurse':
                    for spec_name in spec_names:
                        # Try to find existing specialization by name_ru
                        spec = NurseSpecialization.objects.filter(name_ru=spec_name).first()
                        if not spec:
                            # Create new specialization with unique names
                            try:
                                spec = NurseSpecialization.objects.create(
                                    name_ru=spec_name,
                                    name_kz=f"{spec_name} (KZ)",
                                    name_en=f"{spec_name} (EN)"
                                )
                            except Exception:
                                # If creation fails, try to find by any name field
                                spec = NurseSpecialization.objects.filter(
                                    Q(name_ru=spec_name) |
                                    Q(name_kz=spec_name) |
                                    Q(name_en=spec_name)
                                ).first()
                        if spec:
                            specs.append(spec)

            # Create profile based on role
            if role == 'doctor':
                doctor_profile = DoctorProfile.objects.create(
                    user=new_staff,
                    clinic=clinic,
                    specialization=specs[0] if specs else None,
                    years_of_experience=years_of_experience if years_of_experience else None,
                    offline_consultation_price=offline_consultation_price if offline_consultation_price else None,
                    online_consultation_price=online_consultation_price if online_consultation_price else None,
                    preferred_consultation_duration=preferred_consultation_duration if preferred_consultation_duration else None,
                    online_work_schedule=online_work_schedule if online_work_schedule else None,
                    offline_work_schedule=offline_work_schedule if offline_work_schedule else None,
                    availability_status='offline'
                )
                # Set all specializations in M2M field
                if specs:
                    doctor_profile.specializations.set(specs)

            elif role == 'nurse':
                nurse_profile = NurseProfile.objects.create(
                    user=new_staff,
                    clinic=clinic,
                    specialization=specs[0] if specs else None,
                    years_of_experience=years_of_experience if years_of_experience else None,
                    offline_consultation_price=offline_consultation_price if offline_consultation_price else None,
                    online_consultation_price=online_consultation_price if online_consultation_price else None,
                    preferred_consultation_duration=preferred_consultation_duration if preferred_consultation_duration else None,
                    online_work_schedule=online_work_schedule if online_work_schedule else None,
                    offline_work_schedule=offline_work_schedule if offline_work_schedule else None,
                    availability_status='offline'
                )
                # Set all specializations in M2M field
                if specs:
                    nurse_profile.specializations.set(specs)

            # Get the created profile for response
            profile = None
            if role == 'doctor':
                profile = new_staff.doctor_profile
            elif role == 'nurse':
                profile = new_staff.nurse_profile

            # Return created staff member data
            return Response({
                'id': new_staff.id,
                'first_name': new_staff.first_name,
                'last_name': new_staff.last_name,
                'email': new_staff.email,
                'phone': new_staff.phone,
                'role': new_staff.role,
                'specialization': specialization,
                'gender': new_staff.gender,
                'birth_date': str(new_staff.birth_date) if new_staff.birth_date else '',
                'address': new_staff.address,
                'city': new_staff.city,
                'language': new_staff.language,
                'years_of_experience': profile.years_of_experience if profile else None,
                'offline_consultation_price': str(profile.offline_consultation_price) if profile and profile.offline_consultation_price is not None else None,
                'online_consultation_price': str(profile.online_consultation_price) if profile and profile.online_consultation_price is not None else None,
                'preferred_consultation_duration': profile.preferred_consultation_duration if profile else None,
                'online_work_schedule': profile.online_work_schedule if profile else None,
                'offline_work_schedule': profile.offline_work_schedule if profile else None,
                'is_active': new_staff.is_active,
                'created_at': new_staff.created_at.isoformat() if new_staff.created_at else None,
                'clinic': {
                    'id': clinic.id,
                    'name': clinic.name
                } if clinic else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Error creating staff member")
            return Response(
                {'error': 'Не удалось создать сотрудника', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, pk=None):
        """
        PATCH /api/v1/staff/{id}/
        Update staff member details
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get the staff member
            staff_member = User.objects.get(id=pk, role__in=['doctor', 'nurse'])

            # Check if admin has permission to update this staff member
            admin_profile = None
            try:
                admin_profile = request.user.admin_profile
            except:
                pass

            admin_clinic_id = admin_profile.clinic_id if admin_profile and admin_profile.clinic else None

            # Get staff member's clinic from their profile
            staff_clinic_id = None
            if staff_member.role == 'doctor' and hasattr(staff_member, 'doctor_profile') and staff_member.doctor_profile:
                staff_clinic_id = staff_member.doctor_profile.clinic_id
            elif staff_member.role == 'nurse' and hasattr(staff_member, 'nurse_profile') and staff_member.nurse_profile:
                staff_clinic_id = staff_member.nurse_profile.clinic_id

            if admin_clinic_id and staff_clinic_id != admin_clinic_id:
                return Response(
                    {'error': 'У вас нет прав для изменения этого сотрудника'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Validate email uniqueness if email is being changed
            new_email = request.data.get('email')
            if new_email and new_email != staff_member.email:
                if User.objects.filter(email=new_email).exclude(id=pk).exists():
                    return Response(
                        {'error': 'Пользователь с таким email уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Validate phone uniqueness if phone is being changed
            new_phone = request.data.get('phone')
            if new_phone:
                new_phone = '+' + ''.join(c for c in new_phone if c.isdigit())
            if new_phone and new_phone != staff_member.phone:
                if User.objects.filter(phone=new_phone).exclude(id=pk).exists():
                    return Response(
                        {'error': 'Пользователь с таким телефоном уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Update basic fields if provided
            if 'first_name' in request.data:
                staff_member.first_name = request.data['first_name']
            if 'last_name' in request.data:
                staff_member.last_name = request.data['last_name']
            if 'email' in request.data:
                staff_member.email = request.data['email']
            if 'phone' in request.data:
                staff_member.phone = new_phone

            # Update additional fields if provided
            if 'gender' in request.data:
                staff_member.gender = request.data['gender'] if request.data['gender'] else None
            if 'birth_date' in request.data:
                staff_member.birth_date = request.data['birth_date'] if request.data['birth_date'] else None
            if 'address' in request.data:
                staff_member.address = request.data['address'] if request.data['address'] else None
            if 'city' in request.data:
                staff_member.city = request.data['city'] if request.data['city'] else None
            if 'language' in request.data:
                staff_member.language = request.data['language'] if request.data['language'] else 'ru'

            # Update role if provided (doctor/nurse)
            if 'role' in request.data and request.data['role'] in ['doctor', 'nurse']:
                staff_member.role = request.data['role']

            # Update password if provided
            if 'password' in request.data and request.data['password']:
                password = request.data['password']
                if len(password) < 8:
                    return Response(
                        {'error': 'Пароль должен содержать минимум 8 символов'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                staff_member.set_password(password)

            # Update specializations if provided (supports comma-separated multiple specializations)
            if 'specialization' in request.data:
                specialization_input = request.data['specialization']
                if specialization_input:
                    # Split by comma and strip whitespace
                    spec_names = [s.strip() for s in specialization_input.split(',') if s.strip()]

                    if staff_member.role == 'doctor':
                        specs = []
                        for spec_name in spec_names:
                            # Try to find existing specialization by name_ru
                            spec = DoctorSpecialization.objects.filter(name_ru=spec_name).first()
                            if not spec:
                                # Create new specialization with unique names
                                try:
                                    spec = DoctorSpecialization.objects.create(
                                        name_ru=spec_name,
                                        name_kz=f"{spec_name} (KZ)",
                                        name_en=f"{spec_name} (EN)"
                                    )
                                except Exception:
                                    # If creation fails, try to find by any name field
                                    spec = DoctorSpecialization.objects.filter(
                                        Q(name_ru=spec_name) |
                                        Q(name_kz=spec_name) |
                                        Q(name_en=spec_name)
                                    ).first()
                            if spec:
                                specs.append(spec)

                        # Save user first to ensure profile exists
                        staff_member.save()

                        # Update DoctorProfile with primary specialization and all specializations
                        if hasattr(staff_member, 'doctor_profile'):
                            staff_member.doctor_profile.specialization = specs[0] if specs else None
                            staff_member.doctor_profile.save()
                            # Set all specializations in M2M field
                            if specs:
                                staff_member.doctor_profile.specializations.set(specs)

                    elif staff_member.role == 'nurse':
                        specs = []
                        for spec_name in spec_names:
                            # Try to find existing specialization by name_ru
                            spec = NurseSpecialization.objects.filter(name_ru=spec_name).first()
                            if not spec:
                                # Create new specialization with unique names
                                try:
                                    spec = NurseSpecialization.objects.create(
                                        name_ru=spec_name,
                                        name_kz=f"{spec_name} (KZ)",
                                        name_en=f"{spec_name} (EN)"
                                    )
                                except Exception:
                                    # If creation fails, try to find by any name field
                                    spec = NurseSpecialization.objects.filter(
                                        Q(name_ru=spec_name) |
                                        Q(name_kz=spec_name) |
                                        Q(name_en=spec_name)
                                    ).first()
                            if spec:
                                specs.append(spec)

                        # Save user first to ensure profile exists
                        staff_member.save()

                        # Update NurseProfile with primary specialization and all specializations
                        if hasattr(staff_member, 'nurse_profile'):
                            staff_member.nurse_profile.specialization = specs[0] if specs else None
                            staff_member.nurse_profile.save()
                            # Set all specializations in M2M field
                            if specs:
                                staff_member.nurse_profile.specializations.set(specs)

            # Update is_active if provided (for backward compatibility)
            if 'is_active' in request.data:
                staff_member.is_active = request.data['is_active']

            # Soft delete if requested
            if 'is_deleted' in request.data:
                staff_member.is_deleted = bool(request.data['is_deleted'])

            staff_member.save()

            # Update profile fields if any are provided (including availability_status)
            profile_fields = ['availability_status', 'years_of_experience', 'offline_consultation_price', 'online_consultation_price', 'preferred_consultation_duration', 'online_work_schedule', 'offline_work_schedule', 'clinic_id']
            if any(f in request.data for f in profile_fields):
                profile_defaults = {}
                if 'availability_status' in request.data:
                    profile_defaults['availability_status'] = request.data['availability_status']
                if 'years_of_experience' in request.data:
                    val = request.data['years_of_experience']
                    profile_defaults['years_of_experience'] = int(val) if val else None
                if 'offline_consultation_price' in request.data:
                    val = request.data['offline_consultation_price']
                    profile_defaults['offline_consultation_price'] = val if val else None
                if 'online_consultation_price' in request.data:
                    val = request.data['online_consultation_price']
                    profile_defaults['online_consultation_price'] = val if val else None
                if 'preferred_consultation_duration' in request.data:
                    val = request.data['preferred_consultation_duration']
                    profile_defaults['preferred_consultation_duration'] = int(val) if val else None
                if 'online_work_schedule' in request.data:
                    val = request.data['online_work_schedule']
                    profile_defaults['online_work_schedule'] = val if val else None
                if 'offline_work_schedule' in request.data:
                    val = request.data['offline_work_schedule']
                    profile_defaults['offline_work_schedule'] = val if val else None

                # Update clinic if provided (only for global admins)
                if 'clinic_id' in request.data and not admin_clinic_id:
                    clinic_id = request.data['clinic_id']
                    if clinic_id:
                        from clinics.models import Clinics
                        try:
                            clinic = Clinics.objects.get(id=clinic_id)
                            profile_defaults['clinic'] = clinic
                        except Clinics.DoesNotExist:
                            return Response(
                                {'error': 'Клиника не найдена'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    else:
                        profile_defaults['clinic'] = None

                if staff_member.role == 'doctor':
                    DoctorProfile.objects.update_or_create(user=staff_member, defaults=profile_defaults)
                elif staff_member.role == 'nurse':
                    NurseProfile.objects.update_or_create(user=staff_member, defaults=profile_defaults)

            # Get updated specializations for response (as comma-separated string)
            # Get profile (refresh to pick up updates)
            staff_member.refresh_from_db()
            profile = None
            specialization = None

            if staff_member.role == 'doctor' and hasattr(staff_member, 'doctor_profile'):
                profile = staff_member.doctor_profile
                # Get all specializations from M2M field
                if profile:
                    specs = list(profile.specializations.values_list('name_ru', flat=True))
                    if specs:
                        specialization = ', '.join(specs)
                    elif profile.specialization:
                        specialization = profile.specialization.name_ru
            elif staff_member.role == 'nurse' and hasattr(staff_member, 'nurse_profile'):
                profile = staff_member.nurse_profile
                # Get all specializations from M2M field
                if profile:
                    specs = list(profile.specializations.values_list('name_ru', flat=True))
                    if specs:
                        specialization = ', '.join(specs)
                    elif profile.specialization:
                        specialization = profile.specialization.name_ru

            # Return updated staff member data
            return Response({
                'id': staff_member.id,
                'first_name': staff_member.first_name,
                'last_name': staff_member.last_name,
                'email': staff_member.email,
                'phone': staff_member.phone,
                'role': staff_member.role,
                'specialization': specialization,
                'gender': staff_member.gender,
                'birth_date': str(staff_member.birth_date) if staff_member.birth_date else '',
                'address': staff_member.address,
                'city': staff_member.city,
                'language': staff_member.language,
                'years_of_experience': profile.years_of_experience if profile else None,
                'offline_consultation_price': str(profile.offline_consultation_price) if profile and profile.offline_consultation_price is not None else None,
                'online_consultation_price': str(profile.online_consultation_price) if profile and profile.online_consultation_price is not None else None,
                'preferred_consultation_duration': profile.preferred_consultation_duration if profile else None,
                'online_work_schedule': profile.online_work_schedule if profile else None,
                'offline_work_schedule': profile.offline_work_schedule if profile else None,
                'is_active': staff_member.is_active,
                'availability_status': profile.availability_status if profile else 'offline',
                'created_at': staff_member.created_at.isoformat() if staff_member.created_at else None,
                'clinic': {
                    'id': profile.clinic.id,
                    'name': profile.clinic.name
                } if profile and profile.clinic else None
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'Сотрудник не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("Error updating staff member")
            return Response(
                {'error': 'Не удалось обновить сотрудника', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClinicsViewSet(ViewSet):
    """
    ViewSet for managing clinics.
    Only accessible by authenticated admins.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Get list of all clinics (for global admins to select from)
        """
        try:
            from clinics.models import Clinics

            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get all clinics
            clinics = Clinics.objects.filter(is_deleted=False).order_by('name')

            clinics_data = []
            for clinic in clinics:
                clinics_data.append({
                    'id': clinic.id,
                    'name': clinic.name,
                    'address': clinic.address if hasattr(clinic, 'address') else None,
                    'phone': clinic.phone if hasattr(clinic, 'phone') else None,
                })

            return Response(clinics_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error fetching clinics")
            return Response(
                {'error': 'Не удалось загрузить список клиник', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PatientsViewSet(ViewSet):
    """
    ViewSet for managing patients.
    Only accessible by authenticated admins.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Get list of patients.
        - Global admins: see all patients
        - Clinic admins: see only their clinic's patients
        """
        try:
            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get admin profile to determine clinic access
            admin_profile = None
            try:
                admin_profile = request.user.admin_profile
            except:
                pass

            is_super_admin = admin_profile is None or admin_profile.is_super_admin or (admin_profile and not admin_profile.clinic)
            clinic_id = admin_profile.clinic_id if admin_profile and admin_profile.clinic else None

            # Filter patients based on admin's access level
            if is_super_admin:
                # Super admin: see ALL patients (independent + clinic-assigned)
                patients = User.objects.filter(
                    role='patient',
                    is_deleted=False
                ).order_by('-created_at')
            else:
                # Clinic admin: see ONLY their clinic's patients
                # Patients are associated with clinics through consultations/appointments
                from consultations.models import Consultation
                from appointments.models import HomeAppointment

                # Get patients who have consultations with doctors from this clinic
                # or appointments at this clinic
                patient_ids_from_consultations = Consultation.objects.filter(
                    doctor__doctor_profile__clinic_id=clinic_id
                ).values_list('patient_id', flat=True).distinct()

                patient_ids_from_appointments = HomeAppointment.objects.filter(
                    Q(doctor__doctor_profile__clinic_id=clinic_id) |
                    Q(nurse__nurse_profile__clinic_id=clinic_id)
                ).values_list('patient_id', flat=True).distinct()

                # Combine both sets of patient IDs
                all_patient_ids = set(list(patient_ids_from_consultations) + list(patient_ids_from_appointments))

                # Filter patients by these IDs
                patients = User.objects.filter(
                    id__in=all_patient_ids,
                    role='patient',
                    is_deleted=False
                ).order_by('-created_at')

            patients_data = []
            for patient in patients:
                # Get patient profile data if it exists
                citizenship = None
                marital_status = None
                profession = None
                clinic_data = None
                try:
                    patient_profile = patient.patient_profile
                    citizenship = patient_profile.citizenship
                    marital_status = patient_profile.marital_status
                    profession = patient_profile.profession
                    # Get clinic info if available
                    if patient_profile.clinic:
                        clinic_data = {
                            'id': patient_profile.clinic.id,
                            'name': patient_profile.clinic.name
                        }
                except:
                    pass

                patients_data.append({
                    'id': patient.id,
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'email': patient.email,
                    'phone': patient.phone,
                    'birth_date': str(patient.birth_date) if patient.birth_date else '',
                    'gender': patient.gender,
                    'address': patient.address,
                    'city': patient.city,
                    'citizenship': citizenship,
                    'marital_status': marital_status,
                    'profession': profession,
                    'is_active': patient.is_active,
                    'created_at': patient.created_at.isoformat() if patient.created_at else None,
                    'clinic': clinic_data
                })

            return Response(patients_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error fetching patients")
            return Response(
                {'error': 'Не удалось загрузить список пациентов', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """
        Create a new patient.
        - Global admins can assign to any clinic (or null)
        - Clinic admins automatically assign to their clinic
        """
        try:
            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Extract data from request
            first_name = request.data.get('first_name')
            last_name = request.data.get('last_name')
            email = request.data.get('email')
            phone = request.data.get('phone')
            if phone:
                phone = '+' + ''.join(c for c in phone if c.isdigit())
            password = request.data.get('password')
            birth_date = request.data.get('birth_date')
            gender = request.data.get('gender')
            address = request.data.get('address')
            city = request.data.get('city')
            language = request.data.get('language')

            # Validate required fields
            if not all([first_name, last_name, email, phone, password]):
                return Response(
                    {'error': 'Пожалуйста, заполните все обязательные поля'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                return Response(
                    {'error': 'Пользователь с таким email уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if phone already exists
            if phone and User.objects.filter(phone=phone).exists():
                return Response(
                    {'error': 'Пользователь с таким телефоном уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get admin profile to determine clinic access
            admin_profile = None
            try:
                admin_profile = request.user.admin_profile
            except:
                pass

            is_super_admin = admin_profile is None or admin_profile.is_super_admin or (admin_profile and not admin_profile.clinic)

            # Determine clinic assignment
            if is_super_admin:
                # Super admin: can create independent patients OR assign to any clinic
                clinic_id = request.data.get('clinic_id')  # Optional from request
            else:
                # Clinic admin: NOTE - patients typically don't have direct clinic assignment
                # This is a placeholder for future implementation
                clinic_id = None  # Patients are assigned through consultations/appointments

            clinic = None
            if clinic_id:
                from clinics.models import Clinics
                try:
                    clinic = Clinics.objects.get(id=clinic_id)
                except Clinics.DoesNotExist:
                    return Response(
                        {'error': 'Клиника не найдена'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create new patient
            new_patient = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role='patient',
                birth_date=birth_date if birth_date else None,
                gender=gender,
                address=address,
                city=city,
                language=language if language else 'ru',
                is_active=True,
                is_deleted=False
            )

            # Set password (will be hashed automatically)
            new_patient.set_password(password)
            new_patient.save()

            # Create or update PatientProfile with clinic assignment
            from common.models import PatientProfile
            patient_profile, created = PatientProfile.objects.get_or_create(
                user=new_patient,
                defaults={'clinic': clinic}
            )
            if not created and clinic is not None:
                patient_profile.clinic = clinic
                patient_profile.save()

            # Return created patient data
            return Response({
                'id': new_patient.id,
                'first_name': new_patient.first_name,
                'last_name': new_patient.last_name,
                'email': new_patient.email,
                'phone': new_patient.phone,
                'birth_date': str(new_patient.birth_date) if new_patient.birth_date else '',
                'gender': new_patient.gender,
                'address': new_patient.address,
                'city': new_patient.city,
                'is_active': new_patient.is_active,
                'created_at': new_patient.created_at.isoformat() if new_patient.created_at else None,
                'clinic': {
                    'id': clinic.id,
                    'name': clinic.name
                } if clinic else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Error creating patient")
            return Response(
                {'error': 'Не удалось создать пациента', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, pk=None):
        """
        Update an existing patient (PATCH /api/v1/patients/{id}/)
        """
        try:
            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get the patient to update
            try:
                patient = User.objects.get(id=pk, role='patient', is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Пациент не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update basic fields
            if 'first_name' in request.data:
                patient.first_name = request.data['first_name']
            if 'last_name' in request.data:
                patient.last_name = request.data['last_name']
            if 'email' in request.data:
                email = request.data['email']
                # Check if email is already taken by another user
                if User.objects.filter(email=email).exclude(id=pk).exists():
                    return Response(
                        {'error': 'Пользователь с таким email уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                patient.email = email
            if 'phone' in request.data:
                phone = request.data['phone']
                if phone:
                    phone = '+' + ''.join(c for c in phone if c.isdigit())
                # Check if phone is already taken by another user
                if phone and User.objects.filter(phone=phone).exclude(id=pk).exists():
                    return Response(
                        {'error': 'Пользователь с таким телефоном уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                patient.phone = phone
            if 'birth_date' in request.data:
                patient.birth_date = request.data['birth_date'] if request.data['birth_date'] else None
            if 'gender' in request.data:
                patient.gender = request.data['gender']
            if 'address' in request.data:
                patient.address = request.data['address']
            if 'city' in request.data:
                patient.city = request.data['city']

            # Update password if provided
            if 'password' in request.data and request.data['password']:
                patient.set_password(request.data['password'])

            patient.save()

            # Update clinic assignment in PatientProfile (for super admins)
            admin_profile = None
            try:
                admin_profile = request.user.admin_profile
            except:
                pass

            is_super_admin = admin_profile is None or admin_profile.is_super_admin or (admin_profile and not admin_profile.clinic)

            if is_super_admin and 'clinic_id' in request.data:
                from common.models import PatientProfile
                from clinics.models import Clinics

                clinic_id = request.data['clinic_id']
                clinic = None

                if clinic_id:
                    try:
                        clinic = Clinics.objects.get(id=clinic_id)
                    except Clinics.DoesNotExist:
                        return Response(
                            {'error': 'Клиника не найдена'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Create or update PatientProfile with clinic
                patient_profile, created = PatientProfile.objects.get_or_create(
                    user=patient,
                    defaults={'clinic': clinic}
                )
                if not created:
                    patient_profile.clinic = clinic
                    patient_profile.save()

            # Refresh from database to get proper field types
            patient.refresh_from_db()

            # Get clinic from PatientProfile if it exists
            clinic_data = None
            if hasattr(patient, 'patient_profile') and patient.patient_profile and patient.patient_profile.clinic:
                clinic = patient.patient_profile.clinic
                clinic_data = {
                    'id': clinic.id,
                    'name': clinic.name
                }

            # Return updated patient data
            return Response({
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'email': patient.email,
                'phone': patient.phone,
                'birth_date': str(patient.birth_date) if patient.birth_date else '',
                'gender': patient.gender,
                'address': patient.address,
                'city': patient.city,
                'is_active': patient.is_active,
                'created_at': patient.created_at.isoformat() if patient.created_at else None,
                'clinic': clinic_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error updating patient")
            return Response(
                {'error': 'Не удалось обновить пациента', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportsViewSet(ViewSet):
    """
    ViewSet for generating admin reports and analytics.
    Only accessible by authenticated admins.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/reports/
        Get comprehensive reports with optional date filtering.
        Query params: start (date), end (date)
        """
        from consultations.models import Consultation
        from appointments.models import HomeAppointment
        from payments.models import HomeAppointmentKaspiPayment

        # Check if user is admin
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            return Response(
                {'error': 'У вас нет прав доступа'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse date range from query params
        start_date_str = request.GET.get('start')
        end_date_str = request.GET.get('end')

        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                # Default: beginning of current year
                start_date = datetime(datetime.now().year, 1, 1).date()

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                # Default: today
                end_date = datetime.now().date()
        except ValueError:
            return Response(
                {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get clinic filter if admin is clinic-specific
        admin_profile = None
        try:
            admin_profile = request.user.admin_profile
        except:
            pass

        clinic_id = admin_profile.clinic_id if admin_profile and admin_profile.clinic else None

        # ==================== REVENUE REPORT ====================
        # Get payments for home appointments
        payments_query = HomeAppointmentKaspiPayment.objects.filter(
            status='paid',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        if clinic_id:
            # Filter by appointments where doctor or nurse belongs to the clinic
            payments_query = payments_query.filter(
                Q(appointment__doctor__doctor_profile__clinic_id=clinic_id) |
                Q(appointment__nurse__nurse_profile__clinic_id=clinic_id)
            )

        total_revenue = payments_query.aggregate(total=Sum('amount'))['total'] or 0

        # Monthly revenue
        monthly_revenue_qs = payments_query.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount')
        ).order_by('month')

        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        monthly_revenue = [
            {
                'month': month_names[item['month'].month - 1],
                'revenue': float(item['revenue'] or 0)
            }
            for item in monthly_revenue_qs
        ]

        # Revenue by service type (home appointments for now)
        revenue_by_service = [
            {
                'service': 'Записи на дом',
                'revenue': float(total_revenue),
                'count': payments_query.count()
            }
        ]

        # ==================== CONSULTATION REPORT ====================
        consultations_query = Consultation.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False
        )
        if clinic_id:
            consultations_query = consultations_query.filter(
                doctor__doctor_profile__clinic_id=clinic_id
            )

        total_consultations = consultations_query.count()

        # Consultations by status
        status_mapping = {
            'pending': 'Ожидание',
            'ongoing': 'В процессе',
            'completed': 'Завершено',
            'cancelled': 'Отменено',
            'missed': 'Пропущено',
            'scheduled': 'Запланировано',
        }
        consultations_by_status = consultations_query.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        by_status = [
            {
                'status': status_mapping.get(item['status'], item['status']),
                'count': item['count']
            }
            for item in consultations_by_status
        ]

        # Consultations by doctor (top 10)
        consultations_by_doctor = consultations_query.values(
            'doctor__first_name', 'doctor__last_name', 'doctor_id'
        ).annotate(
            consultations=Count('id')
        ).order_by('-consultations')[:10]

        by_doctor = [
            {
                'doctor_name': f"Доктор {item['doctor__first_name'] or ''} {item['doctor__last_name'] or ''}".strip(),
                'consultations': item['consultations'],
                'revenue': 0  # TODO: Add consultation pricing when available
            }
            for item in consultations_by_doctor
        ]

        # Consultations by specialization
        consultations_by_spec = consultations_query.values(
            'doctor__doctor_profile__specialization__name_ru'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        by_specialization = [
            {
                'specialization': item['doctor__doctor_profile__specialization__name_ru'] or 'Без специализации',
                'count': item['count']
            }
            for item in consultations_by_spec
        ]

        # ==================== APPOINTMENT REPORT ====================
        appointments_query = HomeAppointment.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False
        )
        if clinic_id:
            appointments_query = appointments_query.filter(
                Q(doctor__doctor_profile__clinic_id=clinic_id) | Q(nurse__nurse_profile__clinic_id=clinic_id)
            )

        total_appointments = appointments_query.count()

        # Appointments by status
        appt_status_mapping = {
            'scheduled': 'Запланировано',
            'assigned': 'Назначено',
            'in_progress': 'В процессе',
            'completed': 'Завершено',
            'cancelled': 'Отменено',
        }
        appointments_by_status = appointments_query.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        appt_by_status = [
            {
                'status': appt_status_mapping.get(item['status'], item['status']),
                'count': item['count']
            }
            for item in appointments_by_status
        ]

        # Appointments by nurse (top 10)
        appointments_by_nurse = appointments_query.filter(
            nurse__isnull=False
        ).values(
            'nurse__first_name', 'nurse__last_name'
        ).annotate(
            appointments=Count('id')
        ).order_by('-appointments')[:10]

        by_nurse = [
            {
                'nurse_name': f"Медсестра {item['nurse__first_name'] or ''} {item['nurse__last_name'] or ''}".strip(),
                'appointments': item['appointments']
            }
            for item in appointments_by_nurse
        ]

        # ==================== PATIENT REPORT ====================
        patients_query = User.objects.filter(
            role='patient',
            is_deleted=False
        )
        if clinic_id:
            # Filter patients through consultations/appointments at the clinic
            patient_ids_from_consultations = Consultation.objects.filter(
                doctor__doctor_profile__clinic_id=clinic_id
            ).values_list('patient_id', flat=True).distinct()

            patient_ids_from_appointments = HomeAppointment.objects.filter(
                Q(doctor__doctor_profile__clinic_id=clinic_id) |
                Q(nurse__nurse_profile__clinic_id=clinic_id)
            ).values_list('patient_id', flat=True).distinct()

            all_patient_ids = set(list(patient_ids_from_consultations) + list(patient_ids_from_appointments))
            patients_query = patients_query.filter(id__in=all_patient_ids)

        total_patients = patients_query.count()

        # New patients by month (within date range)
        new_patients_monthly_qs = patients_query.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        new_patients_monthly = [
            {
                'month': month_names[item['month'].month - 1],
                'count': item['count']
            }
            for item in new_patients_monthly_qs
        ]

        # Patients by age group
        today = date.today()

        def calculate_age(birth_date):
            if not birth_date:
                return None
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Get patients with birth dates
        patients_with_age = patients_query.filter(birth_date__isnull=False)

        age_groups = {
            '0-17': 0,
            '18-30': 0,
            '31-50': 0,
            '51-70': 0,
            '70+': 0
        }

        for patient in patients_with_age:
            age = calculate_age(patient.birth_date)
            if age is not None:
                if age <= 17:
                    age_groups['0-17'] += 1
                elif age <= 30:
                    age_groups['18-30'] += 1
                elif age <= 50:
                    age_groups['31-50'] += 1
                elif age <= 70:
                    age_groups['51-70'] += 1
                else:
                    age_groups['70+'] += 1

        by_age_group = [
            {'age_group': group, 'count': count}
            for group, count in age_groups.items()
        ]

        # ==================== COMPILE RESPONSE ====================
        report_data = {
            'revenue_report': {
                'total_revenue': float(total_revenue),
                'monthly_revenue': monthly_revenue,
                'revenue_by_service': revenue_by_service
            },
            'consultation_report': {
                'total_consultations': total_consultations,
                'by_status': by_status,
                'by_doctor': by_doctor,
                'by_specialization': by_specialization
            },
            'appointment_report': {
                'total_appointments': total_appointments,
                'by_status': appt_by_status,
                'by_nurse': by_nurse
            },
            'patient_report': {
                'total_patients': total_patients,
                'new_patients_monthly': new_patients_monthly,
                'by_age_group': by_age_group
            }
        }

        return Response(report_data, status=status.HTTP_200_OK)


class ScheduleViewSet(ViewSet):
    """
    Unified schedule endpoint - merges Consultations and HomeAppointments
    GET  /schedule/          - list all schedule events
    POST /schedule/          - create consultation or appointment
    PATCH /schedule/{id}/    - update status (id format: "consultation_1" or "appointment_2")
    """
    permission_classes = [IsAuthenticated]

    _CONSULT_STATUS_TO_SCHEDULE = {
        'scheduled': 'scheduled',
        'pending': 'scheduled',
        'ongoing': 'in_progress',
        'completed': 'completed',
        'cancelled': 'cancelled',
        'missed': 'cancelled',
    }

    _SCHEDULE_STATUS_TO_CONSULT = {
        'scheduled': 'scheduled',
        'in_progress': 'ongoing',
        'completed': 'completed',
        'cancelled': 'cancelled',
    }

    _APPT_STATUS_TO_SCHEDULE = {
        'scheduled': 'scheduled',
        'assigned': 'scheduled',
        'in_progress': 'in_progress',
        'completed': 'completed',
        'cancelled': 'cancelled',
    }

    def list(self, request):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        from consultations.models import Consultation
        from appointments.models import HomeAppointment

        # Get clinic filter if admin is clinic-specific
        admin_profile = None
        try:
            admin_profile = request.user.admin_profile
        except:
            pass

        clinic_id = admin_profile.clinic_id if admin_profile and admin_profile.clinic else None

        # Scheduled consultations (have scheduled_at)
        consultations = Consultation.objects.filter(
            scheduled_at__isnull=False,
            is_deleted=False
        ).select_related('patient', 'doctor', 'doctor__doctor_profile', 'timeslot')

        if clinic_id:
            consultations = consultations.filter(doctor__doctor_profile__clinic_id=clinic_id)

        # Home appointments
        appointments = HomeAppointment.objects.filter(
            is_deleted=False
        ).select_related('patient', 'doctor', 'nurse')

        if clinic_id:
            appointments = appointments.filter(
                Q(doctor__doctor_profile__clinic_id=clinic_id) | Q(nurse__nurse_profile__clinic_id=clinic_id)
            )

        events = []

        for c in consultations:
            duration = 30
            if c.timeslot:
                duration = int((c.timeslot.end_time - c.timeslot.start_time).total_seconds() / 60)

            specialization = None
            if c.doctor and hasattr(c.doctor, 'doctor_profile') and c.doctor.doctor_profile and c.doctor.doctor_profile.specialization:
                specialization = c.doctor.doctor_profile.specialization.name_ru

            events.append({
                'id': f'consultation_{c.id}',
                'type': 'consultation',
                'patient_id': c.patient_id,
                'patient_name': f"{c.patient.first_name} {c.patient.last_name}",
                'doctor_id': c.doctor_id,
                'doctor_name': f"{c.doctor.first_name} {c.doctor.last_name}" if c.doctor else None,
                'date': c.scheduled_at.strftime('%Y-%m-%d'),
                'time': c.scheduled_at.strftime('%H:%M'),
                'duration': duration,
                'status': self._CONSULT_STATUS_TO_SCHEDULE.get(c.status, 'scheduled'),
                'specialization': specialization,
                'notes': c.session_notes,
            })

        for a in appointments:
            events.append({
                'id': f'appointment_{a.id}',
                'type': 'appointment',
                'patient_id': a.patient_id,
                'patient_name': f"{a.patient.first_name} {a.patient.last_name}",
                'doctor_id': a.doctor_id,
                'doctor_name': f"{a.doctor.first_name} {a.doctor.last_name}" if a.doctor else None,
                'nurse_id': a.nurse_id,
                'nurse_name': f"{a.nurse.first_name} {a.nurse.last_name}" if a.nurse else None,
                'date': a.appointment_time.strftime('%Y-%m-%d'),
                'time': a.appointment_time.strftime('%H:%M'),
                'duration': 60,
                'status': self._APPT_STATUS_TO_SCHEDULE.get(a.status, 'scheduled'),
                'location': a.address,
                'notes': a.notes,
            })

        events.sort(key=lambda e: (e['date'], e['time']))
        return Response(events, status=status.HTTP_200_OK)

    def create(self, request):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        from consultations.models import Consultation, TimeSlot
        from appointments.models import HomeAppointment
        from common.utils.email_utils import send_consultation_created_email

        event_type = request.data.get('type')
        patient_id = request.data.get('patient_id')
        date_str = request.data.get('date')
        time_str = request.data.get('time')
        duration = int(request.data.get('duration', 30))
        notes = request.data.get('notes', '')

        # Validate required fields with user-friendly messages
        missing_fields = []
        if not patient_id:
            missing_fields.append('пациента')
        if not date_str:
            missing_fields.append('дату')
        if not time_str:
            missing_fields.append('время')

        if missing_fields:
            if len(missing_fields) == 1:
                error_msg = f'Пожалуйста, выберите {missing_fields[0]}'
            else:
                error_msg = f'Пожалуйста, заполните следующие поля: {", ".join(missing_fields)}'
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Пациент не найден'}, status=status.HTTP_400_BAD_REQUEST)

        start_dt = timezone.make_aware(
            datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        )

        if event_type == 'consultation':
            doctor_id = request.data.get('doctor_id')
            if not doctor_id:
                return Response({'error': 'doctor_id is required for consultations'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                doctor = User.objects.get(id=doctor_id, role='doctor')
            except User.DoesNotExist:
                return Response({'error': 'Доктор не найден'}, status=status.HTTP_400_BAD_REQUEST)

            end_dt = start_dt + timedelta(minutes=duration)

            try:
                timeslot = TimeSlot.objects.create(
                    doctor=doctor,
                    start_time=start_dt,
                    end_time=end_dt,
                    is_available=False,
                    max_consultations=1,
                    booked_consultations=1,
                )
            except IntegrityError:
                # Timeslot already exists for this doctor at this time
                return Response(
                    {
                        'error': f'У доктора {doctor.first_name} {doctor.last_name} уже есть консультация в это время ({date_str} {time_str}). Пожалуйста, выберите другое время.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            consultation = Consultation.objects.create(
                patient=patient,
                doctor=doctor,
                meeting_id=f"admin-{timezone.now().strftime('%Y%m%d%H%M%S')}-{patient_id}",
                status='scheduled',
                is_urgent=False,
                timeslot=timeslot,
                scheduled_at=start_dt,
                session_notes=notes,
            )

            # Send email notification to patient
            print(f"📧 [ADMIN SCHEDULE] Attempting to send email notification...")
            print(f"   Patient email: {patient.email}")
            print(f"   Access code: {consultation.access_code}")
            print(f"   Scheduled at: {consultation.scheduled_at}")

            try:
                patient_name = f"{patient.first_name} {patient.last_name}".strip() or patient.email.split("@")[0]
                doctor_name = f"{doctor.first_name} {doctor.last_name}".strip() or "Врач"

                # Build consultation link
                consultation_link = f"{settings.FRONTEND_URL}/video-call/patient?meetingId={consultation.meeting_id}"

                print(f"   Patient name: {patient_name}")
                print(f"   Doctor name: {doctor_name}")
                print(f"   Consultation link: {consultation_link}")
                print(f"   Calling send_consultation_created_email()...")

                send_consultation_created_email(
                    patient_email=patient.email,
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    access_code=consultation.access_code,
                    consultation_link=consultation_link,
                    scheduled_at=consultation.scheduled_at,
                    consultation=consultation  # Pass consultation object for magic link token
                )

                print(f"✅ Email sent successfully to {patient.email} with magic link token!")
                logger.info(f"✅ Email sent to {patient.email} for admin-created consultation {consultation.id} with magic link")
            except Exception as email_error:
                # Log error but don't fail the consultation creation
                print(f"❌ [ADMIN SCHEDULE] EMAIL SENDING FAILED!")
                print(f"   Error: {str(email_error)}")
                print(f"   Error type: {type(email_error).__name__}")

                import traceback
                print(f"   Traceback:")
                traceback.print_exc()

                logger.error(f"❌ Failed to send email notification: {str(email_error)}")
                logger.error(f"   Full traceback:", exc_info=True)

            return Response({'id': f'consultation_{consultation.id}'}, status=status.HTTP_201_CREATED)

        elif event_type == 'appointment':
            nurse_id = request.data.get('nurse_id')
            doctor_id = request.data.get('doctor_id')
            address = request.data.get('address', '')

            if not nurse_id and not doctor_id:
                return Response(
                    {'error': 'doctor_id or nurse_id is required for appointments'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            appointment = HomeAppointment.objects.create(
                patient=patient,
                doctor_id=doctor_id if doctor_id else None,
                nurse_id=nurse_id if nurse_id else None,
                appointment_time=start_dt,
                address=address,
                notes=notes,
                status='scheduled',
            )

            return Response({'id': f'appointment_{appointment.id}'}, status=status.HTTP_201_CREATED)

        return Response({'error': 'Invalid event type'}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        from consultations.models import Consultation
        from appointments.models import HomeAppointment

        parts = pk.split('_', 1)
        if len(parts) != 2:
            return Response({'error': 'Invalid event id format'}, status=status.HTTP_400_BAD_REQUEST)

        event_type, event_id = parts[0], parts[1]

        new_status = request.data.get('status')
        if not new_status:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)

        if event_type == 'consultation':
            try:
                consultation = Consultation.objects.get(id=event_id)
            except Consultation.DoesNotExist:
                return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)

            db_status = self._SCHEDULE_STATUS_TO_CONSULT.get(new_status, new_status)
            consultation.status = db_status
            consultation.save()
            return Response({'status': new_status}, status=status.HTTP_200_OK)

        elif event_type == 'appointment':
            try:
                appointment = HomeAppointment.objects.get(id=event_id)
            except HomeAppointment.DoesNotExist:
                return Response({'error': 'Запись не найдена'}, status=status.HTTP_404_NOT_FOUND)

            appointment.status = new_status
            appointment.save()
            return Response({'status': new_status}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid event type'}, status=status.HTTP_400_BAD_REQUEST)
