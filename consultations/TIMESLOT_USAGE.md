# Consultation Timeslot System

This system implements a timeslot-based consultation booking system that integrates with AI urgency recommendations.

## How It Works

1. **AI Recommendation**: When a patient submits symptoms, AI analyzes them and determines urgency level
2. **Urgent Consultations**: If AI marks as urgent, consultation is created immediately (no timeslot needed)
3. **Non-Urgent Consultations**: If AI marks as non-urgent, patient selects from available timeslots

## Key Components

### Models

- **TimeSlot**: Represents available appointment slots for doctors
- **Consultation**: Extended with timeslot and AI recommendation relationships
- **AIRecommendationLog**: Contains urgency field that drives the booking flow

### Services

- **ConsultationBookingService**: Handles the booking logic
- **TimeslotManagementService**: Manages doctor timeslots

## API Endpoints

### 1. Process AI Recommendation
```
POST /api/consultations/ai-process/
{
    "ai_recommendation_id": 123,
    "preferred_doctor_id": 456  // optional
}
```

**Response for Urgent:**
```json
{
    "is_urgent": true,
    "consultation": {...},
    "message": "Экстренная консультация создана. Врач свяжется с вами в ближайшее время."
}
```

**Response for Non-Urgent:**
```json
{
    "is_urgent": false,
    "available_timeslots": [...],
    "message": "Выберите удобное время для консультации."
}
```

### 2. Book Scheduled Consultation
```
POST /api/consultations/book-scheduled/
{
    "timeslot_id": 123,
    "ai_recommendation_id": 456,
    "scheduled_time": "2024-01-15T10:30:00Z"
}
```

### 3. Get Available Timeslots
```
GET /api/consultations/timeslots/available/?doctor_id=123&start_date=2024-01-15&end_date=2024-01-20
```

### 4. Patient Consultations
```
GET /api/consultations/my-consultations/?status=scheduled&include_past=false
```

### 5. Cancel/Reschedule
```
POST /api/consultations/{id}/cancel/
POST /api/consultations/{id}/reschedule/
```

## Usage Examples

### 1. Complete Patient Flow

```python
# Step 1: AI processes symptoms and determines urgency
ai_recommendation = AIRecommendationLog.objects.create(
    symptoms="Головная боль, температура 38.5",
    urgency="non_urgent",  # or "urgent"
    recommended_specialty="терапия"
)

# Step 2: Process the recommendation
result = ConsultationBookingService.process_ai_recommendation(
    patient=patient,
    ai_recommendation=ai_recommendation
)

if result['is_urgent']:
    # Urgent consultation created automatically
    consultation = result['consultation']
    print(f"Urgent consultation created: {consultation.meeting_id}")
else:
    # Show available timeslots to patient
    timeslots = result['available_timeslots']
    for slot in timeslots:
        print(f"Available: {slot.start_time} - {slot.end_time}")

    # Patient selects a timeslot
    selected_timeslot = timeslots[0]
    consultation = ConsultationBookingService.book_scheduled_consultation(
        patient=patient,
        timeslot=selected_timeslot,
        ai_recommendation=ai_recommendation
    )
    print(f"Scheduled consultation: {consultation.scheduled_at}")
```

### 2. Doctor Timeslot Management

```python
# Generate timeslots for a doctor
slots_created = TimeslotManagementService.bulk_create_timeslots(
    doctor=doctor,
    start_date=date(2024, 1, 15),
    end_date=date(2024, 1, 30),
    start_hour=9,
    end_hour=18,
    slot_duration_minutes=30,
    weekdays_only=True
)

# Block timeslots for vacation
blocked = TimeslotManagementService.block_timeslots(
    doctor=doctor,
    start_time=datetime(2024, 1, 20, 0, 0),
    end_time=datetime(2024, 1, 25, 23, 59),
    reason="Отпуск"
)
```

## Management Commands

### Generate Doctor Timeslots
```bash
# Generate 30 days of timeslots for all doctors
python manage.py generate_doctor_timeslots --days 30

# Generate for specific doctor
python manage.py generate_doctor_timeslots --doctor-id 123 --days 14

# Custom schedule (9 AM - 6 PM, 30-minute slots, weekdays only)
python manage.py generate_doctor_timeslots \
    --start-hour 9 \
    --end-hour 18 \
    --slot-duration 30 \
    --weekdays-only
```

## Database Migrations

Run these commands to apply the new models:

```bash
python manage.py makemigrations consultations
python manage.py migrate consultations
```

## Key Features

### 1. AI-Driven Urgency
- **Urgent**: Immediate consultation creation, no timeslot needed
- **Non-urgent**: Patient chooses from available timeslots

### 2. Flexible Timeslots
- Doctors can set custom availability
- Support for recurring slots
- Overbooking protection
- Automatic booking/cancellation management

### 3. Smart Booking
- Validates timeslot availability
- Prevents double-booking
- Handles cancellations and reschedules
- Tracks consultation history

### 4. Doctor Management
- Bulk timeslot generation
- Block periods for vacation/breaks
- View scheduled consultations
- Availability tracking

## Status Flow

```
AI Recommendation Created
    ↓
Is Urgent?
    ├─ Yes → Immediate Consultation (status: pending)
    ├─ No → Patient Selects Timeslot
                ↓
            Consultation Created (status: scheduled)
                ↓
            Doctor Starts Call (status: ongoing)
                ↓
            Call Ends (status: completed)
```

## Best Practices

1. **Always check AI urgency** before showing timeslots
2. **Validate timeslot availability** before booking
3. **Use transactions** for booking operations
4. **Handle timeslot conflicts** gracefully
5. **Provide clear error messages** to users
6. **Monitor booking patterns** for optimization

## Error Handling

Common errors and solutions:

- **Timeslot unavailable**: Show alternative times
- **Doctor not found**: Suggest similar specialists
- **AI recommendation required**: Ensure AI analysis is complete
- **Urgent consultation cannot be scheduled**: Use immediate booking flow