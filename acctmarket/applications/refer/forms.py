from django import forms


class WalletFundingForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,  # Ensures only positive values
        label="Amount to Add",
        widget=forms.NumberInput(attrs={
            "placeholder": "$120",
            "class": "crancy__item-input"
        })
    )
