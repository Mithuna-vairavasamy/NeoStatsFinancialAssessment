from typing import Any


DEFAULT_TOLERANCE = 0.01


class FinancialValidationService:
    """
    Deterministic financial calculation validation.

    No AI is used here.
    """

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE):
        self.tolerance = tolerance

    def approximately_equal(
        self,
        actual: float | None,
        expected: float | None,
    ) -> bool:
        if actual is None or expected is None:
            return False

        return abs(actual - expected) <= self.tolerance

    def _check(
        self,
        name: str,
        formula: str,
        operands: dict[str, Any],
        calculated_value: float | None,
        reported_value: float | None,
    ) -> dict[str, Any]:
        """
        Create one financial validation check.

        If required values are missing, the check is
        NOT_APPLICABLE rather than FAIL.
        """

        if calculated_value is None or reported_value is None:
            return {
                "name": name,
                "formula": formula,
                "operands": operands,
                "calculated_value": calculated_value,
                "reported_value": reported_value,
                "variance": None,
                "status": "NOT_APPLICABLE",
            }

        variance = reported_value - calculated_value

        return {
            "name": name,
            "formula": formula,
            "operands": operands,
            "calculated_value": calculated_value,
            "reported_value": reported_value,
            "variance": variance,
            "status": (
                "PASS"
                if self.approximately_equal(
                    reported_value,
                    calculated_value,
                )
                else "FAIL"
            ),
        }

    def _build_result(
        self,
        checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build the final validation result.

        Rules:
        - Any FAIL -> overall FAIL
        - All NOT_APPLICABLE -> overall NOT_APPLICABLE
        - Otherwise -> PASS
        """

        applicable_checks = [
            check
            for check in checks
            if check["status"] != "NOT_APPLICABLE"
        ]

        failed_checks = [
            check
            for check in checks
            if check["status"] == "FAIL"
        ]

        if failed_checks:
            overall_status = "FAIL"
        elif not applicable_checks:
            overall_status = "NOT_APPLICABLE"
        else:
            overall_status = "PASS"

        issues = [
            check["name"]
            for check in failed_checks
        ]

        return {
            "checks": checks,
            "overall_status": overall_status,
            "issues": issues,
        }

    def validate_invoice(
        self,
        line_items: list[dict[str, Any]],
        subtotal: float | None = None,
        tax_amount: float | None = None,
        discount: float | None = None,
        round_off: float | None = None,
        total_amount: float | None = None,
        cash_paid: float | None = None,
        change: float | None = None,
    ) -> dict[str, Any]:
        """
        Validate invoice financial calculations.

        Required assessment checks:
        1. quantity × unit price ≈ line total
        2. sum of line totals ≈ subtotal
        3. taxable amount + tax - discount + applicable
           round-off ≈ total
        4. cash paid - total ≈ change, when those values exist
        """

        checks: list[dict[str, Any]] = []


        line_total_sum = 0.0
        all_line_totals_available = bool(line_items)

        for index, item in enumerate(line_items, start=1):
            quantity = item.get("quantity")
            unit_price = item.get("unit_price")
            line_total = item.get("line_total")

            calculated_line_total: float | None = None

            if quantity is not None and unit_price is not None:
                calculated_line_total = quantity * unit_price

            checks.append(
                self._check(
                    name=f"invoice_line_total_check_{index}",
                    formula="quantity * unit_price",
                    operands={
                        "line_number": index,
                        "quantity": quantity,
                        "unit_price": unit_price,
                    },
                    calculated_value=calculated_line_total,
                    reported_value=line_total,
                )
            )

            if line_total is None:
                all_line_totals_available = False
            else:
                line_total_sum += line_total


        checks.append(
            self._check(
                name="invoice_subtotal_check",
                formula="sum(line_totals)",
                operands={
                    "line_totals_available":
                        all_line_totals_available,
                },
                calculated_value=(
                    line_total_sum
                    if all_line_totals_available
                    else None
                ),
                reported_value=subtotal,
            )
        )

        calculated_total: float | None = None

        if (
            subtotal is not None
            and tax_amount is not None
            and discount is not None
        ):
            calculated_total = (
                subtotal
                + tax_amount
                - discount
                + (round_off or 0)
            )

        checks.append(
            self._check(
                name="invoice_total_check",
                formula=(
                    "subtotal + tax_amount - discount "
                    "+ round_off"
                ),
                operands={
                    "subtotal": subtotal,
                    "tax_amount": tax_amount,
                    "discount": discount,
                    "round_off": round_off,
                },
                calculated_value=calculated_total,
                reported_value=total_amount,
            )
        )


        calculated_change: float | None = None

        if (
            cash_paid is not None
            and total_amount is not None
        ):
            calculated_change = cash_paid - total_amount

        checks.append(
            self._check(
                name="invoice_cash_change_check",
                formula="cash_paid - total_amount",
                operands={
                    "cash_paid": cash_paid,
                    "total_amount": total_amount,
                },
                calculated_value=calculated_change,
                reported_value=change,
            )
        )

        return self._build_result(checks)

    def validate_balance_sheet_period(
        self,
        total_assets: float | None,
        total_capital_and_liabilities: float | None,
    ) -> dict[str, Any]:
        """
        Validate one Balance Sheet period.

        Core assessment rule:
        Total Capital & Liabilities ≈ Total Assets.
        """

        checks = [
            self._check(
                name="balance_sheet_reconciliation",
                formula="total_capital_and_liabilities",
                operands={
                    "total_capital_and_liabilities":
                        total_capital_and_liabilities,
                },
                calculated_value=total_capital_and_liabilities,
                reported_value=total_assets,
            )
        ]

        return self._build_result(checks)

    def validate_balance_sheet(
        self,
        periods: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Validate every Balance Sheet comparative period independently.
        """

        checks: list[dict[str, Any]] = []

        for period in periods:
            label = period.get("label")
            values = period.get("values", {})

            total_assets = values.get("total_assets")

            total_capital_and_liabilities = values.get(
                "total_capital_and_liabilities"
            )

            check = self._check(
                name="balance_sheet_reconciliation",
                formula="total_capital_and_liabilities",
                operands={
                    "period": label,
                    "total_capital_and_liabilities":
                        total_capital_and_liabilities,
                },
                calculated_value=total_capital_and_liabilities,
                reported_value=total_assets,
            )

            checks.append(check)

        return self._build_result(checks)

    def validate_profit_and_loss_period(
        self,
        interest_earned: float | None,
        other_income: float | None,
        total_income: float | None,
        interest_expended: float | None,
        operating_expenses: float | None,
        provisions_and_contingencies: float | None,
        total_expenditure: float | None,
        net_profit_before_minority_interest: float | None,
        minority_interest: float | None,
        share_in_profits_of_associates: float | None,
        consolidated_net_profit: float | None,
    ) -> dict[str, Any]:
        """
        Validate one Profit & Loss period.

        Assessment rules:

        Total Income
            = Interest Earned + Other Income

        Total Expenditure
            = Interest Expended
            + Operating Expenses
            + Provisions & Contingencies

        Net Profit before Minority Interest
            = Total Income - Total Expenditure

        Consolidated Net Profit attributable to Group
            = Net Profit before Minority Interest
            - Minority Interest
            + Share in Profits of Associates
        """

        checks: list[dict[str, Any]] = []

        calculated_total_income: float | None = None

        if (
            interest_earned is not None
            and other_income is not None
        ):
            calculated_total_income = (
                interest_earned
                + other_income
            )

        checks.append(
            self._check(
                name="total_income_check",
                formula="interest_earned + other_income",
                operands={
                    "interest_earned": interest_earned,
                    "other_income": other_income,
                },
                calculated_value=calculated_total_income,
                reported_value=total_income,
            )
        )


        calculated_total_expenditure: float | None = None

        if (
            interest_expended is not None
            and operating_expenses is not None
            and provisions_and_contingencies is not None
        ):
            calculated_total_expenditure = (
                interest_expended
                + operating_expenses
                + provisions_and_contingencies
            )

        checks.append(
            self._check(
                name="total_expenditure_check",
                formula=(
                    "interest_expended + operating_expenses "
                    "+ provisions_and_contingencies"
                ),
                operands={
                    "interest_expended": interest_expended,
                    "operating_expenses": operating_expenses,
                    "provisions_and_contingencies":
                        provisions_and_contingencies,
                },
                calculated_value=calculated_total_expenditure,
                reported_value=total_expenditure,
            )
        )


        calculated_net_profit_before_minority: float | None = None

        if (
            total_income is not None
            and total_expenditure is not None
        ):
            calculated_net_profit_before_minority = (
                total_income
                - total_expenditure
            )

        checks.append(
            self._check(
                name="net_profit_before_minority_interest_check",
                formula="total_income - total_expenditure",
                operands={
                    "total_income": total_income,
                    "total_expenditure": total_expenditure,
                },
                calculated_value=(
                    calculated_net_profit_before_minority
                ),
                reported_value=(
                    net_profit_before_minority_interest
                ),
            )
        )


        calculated_consolidated_net_profit: float | None = None

        if (
            net_profit_before_minority_interest is not None
            and minority_interest is not None
            and share_in_profits_of_associates is not None
        ):
            calculated_consolidated_net_profit = (
                net_profit_before_minority_interest
                - minority_interest
                + share_in_profits_of_associates
            )

        checks.append(
            self._check(
                name="consolidated_net_profit_check",
                formula=(
                    "net_profit_before_minority_interest "
                    "- minority_interest "
                    "+ share_in_profits_of_associates"
                ),
                operands={
                    "net_profit_before_minority_interest":
                        net_profit_before_minority_interest,
                    "minority_interest":
                        minority_interest,
                    "share_in_profits_of_associates":
                        share_in_profits_of_associates,
                },
                calculated_value=(
                    calculated_consolidated_net_profit
                ),
                reported_value=consolidated_net_profit,
            )
        )

        return self._build_result(checks)

    def validate_profit_and_loss(
        self,
        periods: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Validate every Profit & Loss comparative period independently.
        """

        checks: list[dict[str, Any]] = []

        for period in periods:
            values = period.get("values", {})

            result = self.validate_profit_and_loss_period(
                interest_earned=values.get(
                    "interest_earned"
                ),
                other_income=values.get(
                    "other_income"
                ),
                total_income=values.get(
                    "total_income"
                ),
                interest_expended=values.get(
                    "interest_expended"
                ),
                operating_expenses=values.get(
                    "operating_expenses"
                ),
                provisions_and_contingencies=values.get(
                    "provisions_and_contingencies"
                ),
                total_expenditure=values.get(
                    "total_expenditure"
                ),
                net_profit_before_minority_interest=values.get(
                    "net_profit_before_minority_interest"
                ),
                minority_interest=values.get(
                    "minority_interest"
                ),
                share_in_profits_of_associates=values.get(
                    "share_in_profits_of_associates"
                ),
                consolidated_net_profit=values.get(
                    "consolidated_net_profit_attributable_to_group"
                ),
            )

            checks.extend(result["checks"])

        return self._build_result(checks)


    def validate_cash_flow_period(
        self,
        operating_cash_flow: float | None,
        investing_cash_flow: float | None,
        financing_cash_flow: float | None,
        fx_adjustment: float | None,
        net_increase_in_cash: float | None,
        opening_cash: float | None,
        closing_cash: float | None,
        cash_and_cash_equivalents_on_amalgamation: float | None = None,
    ) -> dict[str, Any]:
        """
        Validate one Cash Flow period.

        Assessment rules:

        Net Increase in Cash
            = Operating
            + Investing
            + Financing
            + FX / Translation Adjustment
            + applicable adjustments

        Closing Cash
            = Opening Cash + Net Increase in Cash
        """

        checks: list[dict[str, Any]] = []

        calculated_net_increase: float | None = None

        if (
            operating_cash_flow is not None
            and investing_cash_flow is not None
            and financing_cash_flow is not None
            and fx_adjustment is not None
        ):
            calculated_net_increase = (
                operating_cash_flow
                + investing_cash_flow
                + financing_cash_flow
                + fx_adjustment
                + (
                    cash_and_cash_equivalents_on_amalgamation
                    or 0
                )
            )

        checks.append(
            self._check(
                name="cash_flow_net_increase_check",
                formula=(
                    "operating_cash_flow "
                    "+ investing_cash_flow "
                    "+ financing_cash_flow "
                    "+ fx_adjustment "
                    "+ cash_and_cash_equivalents_on_amalgamation"
                ),
                operands={
                    "operating_cash_flow":
                        operating_cash_flow,
                    "investing_cash_flow":
                        investing_cash_flow,
                    "financing_cash_flow":
                        financing_cash_flow,
                    "fx_adjustment":
                        fx_adjustment,
                    "cash_and_cash_equivalents_on_amalgamation":
                        cash_and_cash_equivalents_on_amalgamation,
                },
                calculated_value=calculated_net_increase,
                reported_value=net_increase_in_cash,
            )
        )


        calculated_closing_cash: float | None = None

        if (
            opening_cash is not None
            and net_increase_in_cash is not None
        ):
            calculated_closing_cash = (
                opening_cash
                + net_increase_in_cash
            )

        checks.append(
            self._check(
                name="cash_flow_closing_cash_check",
                formula="opening_cash + net_increase_in_cash",
                operands={
                    "opening_cash": opening_cash,
                    "net_increase_in_cash":
                        net_increase_in_cash,
                },
                calculated_value=calculated_closing_cash,
                reported_value=closing_cash,
            )
        )

        return self._build_result(checks)

    def validate_cash_flow(
        self,
        periods: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Validate every Cash Flow comparative period independently.
        """

        checks: list[dict[str, Any]] = []

        for period in periods:
            values = period.get("values", {})

            result = self.validate_cash_flow_period(
                operating_cash_flow=values.get(
                    "operating_cash_flow"
                ),
                investing_cash_flow=values.get(
                    "investing_cash_flow"
                ),
                financing_cash_flow=values.get(
                    "financing_cash_flow"
                ),
                fx_adjustment=values.get(
                    "fx_adjustment"
                ),
                net_increase_in_cash=values.get(
                    "net_increase_in_cash"
                ),
                opening_cash=values.get(
                    "opening_cash"
                ),
                closing_cash=values.get(
                    "closing_cash"
                ),
                cash_and_cash_equivalents_on_amalgamation=values.get(
                    "cash_and_cash_equivalents_on_amalgamation"
                ),
            )

            checks.extend(result["checks"])

        return self._build_result(checks)