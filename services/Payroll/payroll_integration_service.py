from sqlalchemy.orm import Session


class PayrollIntegrationService:
    def __init__(self, db: Session):
        self.db = db

    # ── Dashboard ─────────────────────────────────────────────────────────────
    def get_dashboard_summary(self, month, department, location):
        raise NotImplementedError

    # ── Settings ──────────────────────────────────────────────────────────────
    def get_settings(self):
        raise NotImplementedError

    def update_settings(self, data):
        raise NotImplementedError

    # ── Sync ──────────────────────────────────────────────────────────────────
    def trigger_sync(self, data):
        raise NotImplementedError

    def get_sync_logs(self, sync_type, limit):
        raise NotImplementedError

    def get_sync_status(self):
        raise NotImplementedError

    # ── Freeze ────────────────────────────────────────────────────────────────
    def get_freeze_status(self):
        raise NotImplementedError

    def create_freeze_period(self, data):
        raise NotImplementedError

    def freeze_now(self, frozen_by):
        raise NotImplementedError

    def unfreeze(self, unfrozen_by):
        raise NotImplementedError

    # ── Payroll Calculation ───────────────────────────────────────────────────
    def get_payroll_calculation(self, period_month, department):
        raise NotImplementedError

    def run_payroll(self, data):
        raise NotImplementedError

    def export_payroll_data(self, period_month):
        raise NotImplementedError

    # ── Calculation Rules ─────────────────────────────────────────────────────
    def list_calculation_rules(self):
        raise NotImplementedError

    def create_calculation_rule(self, data):
        raise NotImplementedError

    def update_calculation_rule(self, rule_id, data):
        raise NotImplementedError

    def toggle_calculation_rule(self, rule_id):
        raise NotImplementedError

    # ── Corrections ───────────────────────────────────────────────────────────
    def list_corrections(self, status, employee_id):
        raise NotImplementedError

    def add_correction(self, data):
        raise NotImplementedError

    def review_correction(self, correction_id, decision, data):
        raise NotImplementedError

    def export_corrections(self):
        raise NotImplementedError

    # ── Alerts ────────────────────────────────────────────────────────────────
    def list_alerts(self, is_resolved):
        raise NotImplementedError

    def resolve_alert(self, alert_id, data):
        raise NotImplementedError

    # ── Reports ───────────────────────────────────────────────────────────────
    def list_reports(self):
        raise NotImplementedError

    def generate_report(self, report_id, format):
        raise NotImplementedError
