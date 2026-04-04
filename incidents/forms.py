from django import forms

from .models import Incident, StatusUpdate


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = [
            'title', 'description', 'incident_type', 'priority',
            'latitude', 'longitude', 'address', 'area', 'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief title of the issue',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe the issue in detail',
            }),
            'incident_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address (click map to auto-fill or enter manually)',
            }),
            'area': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Area / Ward / Zone',
            }),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitude')
        lng = cleaned_data.get('longitude')

        if lat is None or lng is None:
            raise forms.ValidationError(
                'Location is required. Use "Use My Current Location" or click on the map.'
            )

        if lat < -90 or lat > 90:
            self.add_error('latitude', 'Latitude must be between -90 and 90.')

        if lng < -180 or lng > 180:
            self.add_error('longitude', 'Longitude must be between -180 and 180.')

        return cleaned_data


class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = StatusUpdate
        fields = ['status', 'note']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Optional note about this update',
            }),
        }
