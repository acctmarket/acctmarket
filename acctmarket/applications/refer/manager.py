from decimal import Decimal

from django.db import models


class ReferralManager(models.Manager):
    def completed(self):
        """Returns only completed referrals."""
        return self.filter(is_completed=True)

    def referrals_by_user(self, user):
        """
        Retrieves a kaleidoscopic tapestry of users referred by the specified
        user,
        capturing each user without needing to complete the referral journey.

        Parameters:
        - user (User): The user who referred others.

        Returns:
        - QuerySet: List of referrals initiated by the given user.
        """
        return self.filter(referrer=user).select_related("referred_user")

    def by_spend_threshold(self, minimum_spend=Decimal("0.00")):
        """
        Returns referrals where referred users have spent
        more than a specified amount.

        Args:
            minimum_spend (Decimal): Minimum amount spent by referred users.
        """
        return self.filter(total_referred_spend__gte=minimum_spend)

    def in_tier(self, tier):
        """
        Returns referrals for users in a specified referral tier.

        Args:
            tier (str): The referral tier to filter by
            (e.g., "Starter", "Power", "Elite").
        """
        return self.filter(referrer__profile__referral_tier=tier)

    def active_within_period(self, start_date, end_date):
        """
        Returns referrals created within a specific date range.

        Args:
            start_date (date): The start of the date range.
            end_date (date): The end of the date range.
        """
        return self.filter(created_at__range=(start_date, end_date))

    def referral_stats(self, user):
        """
        Returns aggregated stats for a user's referrals,
        including total and average spend.

        Args:
            user: The user for whom to gather referral stats.

        Returns:
            dict: A dictionary with total and average referred user spending.
        """
        completed_referrals = self.for_user(user).completed()
        total_spend = completed_referrals.aggregate(
            total=models.Sum(
                "total_referred_spend",
            )
        )["total"] or Decimal("0.00")
        average_spend = completed_referrals.aggregate(
            avg=models.Avg("total_referred_spend"),
        )["avg"] or Decimal("0.00")

        return {
            "total_spend": total_spend,
            "average_spend": average_spend,
            "completed_count": completed_referrals.count(),
        }
