from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Layer = Literal["technical", "org_legal", "economic_management"]
CostType = Literal["preventive", "detection", "recovery", "legal_compliance"]
ThreatMechanism = Literal[
    "confidentiality",
    "integrity",
    "availability",
    "legal_noncompliance",
    "fraud",
]


@dataclass(frozen=True)
class Asset:
    id: str
    name: str
    category: str
    layer_weight: dict[str, float]
    default_criticality: float
    revenue_dependency: float
    legal_dependency: float


@dataclass(frozen=True)
class Threat:
    id: str
    name: str
    asset_ids: list[str]
    mechanism: ThreatMechanism
    layer: Layer
    base_likelihood: float
    default_loss_share: float
    heavy_tail: float
    description: str


@dataclass(frozen=True)
class Control:
    id: str
    name: str
    layer: Layer
    cost_type: CostType
    annual_cost: int
    affected_threats: list[str]
    probability_reduction: float
    loss_reduction: float
    downtime_reduction: float
    min_business_size: str = "micro"


ASSETS: list[Asset] = [
    Asset(
        "email",
        "Корпоративная почта и мессенджеры",
        "communications",
        {"technical": 0.45, "org_legal": 0.35, "economic_management": 0.20},
        0.82,
        0.65,
        0.35,
    ),
    Asset(
        "website",
        "Сайт, формы заявок, интернет-магазин",
        "sales",
        {"technical": 0.55, "org_legal": 0.20, "economic_management": 0.25},
        0.78,
        0.85,
        0.30,
    ),
    Asset(
        "pos",
        "Онлайн-касса, терминалы, эквайринг",
        "payments",
        {"technical": 0.45, "org_legal": 0.15, "economic_management": 0.40},
        0.86,
        0.90,
        0.15,
    ),
    Asset(
        "crm",
        "CRM и клиентская база",
        "data",
        {"technical": 0.35, "org_legal": 0.45, "economic_management": 0.20},
        0.88,
        0.70,
        0.80,
    ),
    Asset(
        "personal_data",
        "Персональные данные клиентов и сотрудников",
        "regulated_data",
        {"technical": 0.25, "org_legal": 0.60, "economic_management": 0.15},
        0.90,
        0.30,
        1.00,
    ),
    Asset(
        "cloud",
        "Облачные сервисы, файлы, SaaS",
        "infrastructure",
        {"technical": 0.45, "org_legal": 0.30, "economic_management": 0.25},
        0.76,
        0.60,
        0.45,
    ),
    Asset(
        "bank",
        "Банк-клиент и платёжные кабинеты",
        "finance",
        {"technical": 0.50, "org_legal": 0.20, "economic_management": 0.30},
        0.95,
        0.75,
        0.25,
    ),
    Asset(
        "employees",
        "Сотрудники, подрядчики, внутренние доступы",
        "people",
        {"technical": 0.20, "org_legal": 0.55, "economic_management": 0.25},
        0.80,
        0.45,
        0.70,
    ),
]


THREATS: list[Threat] = [
    Threat(
        "phishing_email",
        "Фишинг и захват корпоративной почты",
        ["email", "bank", "crm"],
        "fraud",
        "technical",
        0.52,
        0.22,
        1.45,
        "Риск компрометации почты, платёжных инструкций, договорной переписки и доступа к кабинетам.",
    ),
    Threat(
        "ransomware",
        "Шифровальщик и блокировка рабочих данных",
        ["cloud", "crm", "personal_data"],
        "availability",
        "technical",
        0.22,
        0.28,
        1.85,
        "Редкое, но тяжёлое событие: остановка процессов, восстановление данных, простой.",
    ),
    Threat(
        "website_outage",
        "Падение сайта или интернет-магазина",
        ["website"],
        "availability",
        "technical",
        0.38,
        0.18,
        1.25,
        "Потеря заявок, рекламного трафика и доверия клиентов.",
    ),
    Threat(
        "pos_outage",
        "Остановка кассы, терминалов или эквайринга",
        ["pos"],
        "availability",
        "economic_management",
        0.34,
        0.20,
        1.15,
        "Прямой простой продаж, особенно критичен для торговли, услуг и HoReCa.",
    ),
    Threat(
        "insider_leak",
        "Инсайдерская выгрузка клиентской базы",
        ["crm", "personal_data", "employees"],
        "confidentiality",
        "org_legal",
        0.20,
        0.31,
        1.95,
        "Скрытый конкурентный ущерб: уход клиентов, копирование базы, снижение маржинальности.",
    ),
    Threat(
        "pdn_leak",
        "Утечка персональных данных",
        ["personal_data", "crm", "cloud"],
        "confidentiality",
        "org_legal",
        0.18,
        0.36,
        2.10,
        "Правовой, репутационный и восстановительный ущерб.",
    ),
    Threat(
        "account_takeover",
        "Захват облачных, рекламных или платёжных кабинетов",
        ["cloud", "website", "bank", "email"],
        "integrity",
        "technical",
        0.30,
        0.24,
        1.55,
        "Потеря контроля над каналами продаж, платежами и данными.",
    ),
    Threat(
        "legal_gap_pdn",
        "Правовой разрыв в обработке персональных данных",
        ["personal_data", "website", "employees"],
        "legal_noncompliance",
        "org_legal",
        0.46,
        0.26,
        1.60,
        "Отсутствие документов, уведомлений, оснований обработки, договоров и процедур реагирования.",
    ),
    Threat(
        "supplier_failure",
        "Отказ ИТ-поставщика, хостинга или облачного сервиса",
        ["cloud", "website", "pos", "crm"],
        "availability",
        "economic_management",
        0.28,
        0.19,
        1.35,
        "Зависимость от внешнего сервиса без резервного сценария.",
    ),
]


CONTROLS: list[Control] = [
    Control(
        "mfa",
        "MFA для почты, облаков, банка и администраторов",
        "technical",
        "preventive",
        18000,
        ["phishing_email", "account_takeover"],
        0.42,
        0.12,
        0.00,
    ),
    Control(
        "backup_tested",
        "Резервное копирование с проверкой восстановления",
        "technical",
        "recovery",
        42000,
        ["ransomware", "supplier_failure"],
        0.10,
        0.48,
        0.38,
    ),
    Control(
        "email_hardening",
        "Настройка домена почты, антифишинг, SPF/DKIM/DMARC",
        "technical",
        "preventive",
        26000,
        ["phishing_email", "account_takeover"],
        0.28,
        0.10,
        0.00,
    ),
    Control(
        "access_control",
        "Разграничение доступов к CRM, файлам и клиентской базе",
        "org_legal",
        "preventive",
        36000,
        ["insider_leak", "pdn_leak", "account_takeover"],
        0.26,
        0.30,
        0.00,
    ),
    Control(
        "offboarding",
        "Порядок увольнения: отзыв доступов, акты, контроль выгрузок",
        "org_legal",
        "preventive",
        22000,
        ["insider_leak", "pdn_leak"],
        0.22,
        0.24,
        0.00,
    ),
    Control(
        "pdn_compliance",
        "Правовой комплект ПДн: политика, основания, уведомления, договоры",
        "org_legal",
        "legal_compliance",
        65000,
        ["legal_gap_pdn", "pdn_leak"],
        0.35,
        0.42,
        0.00,
    ),
    Control(
        "incident_procedure",
        "Процедура реагирования на инциденты и утечки",
        "org_legal",
        "detection",
        32000,
        ["pdn_leak", "legal_gap_pdn", "ransomware"],
        0.14,
        0.32,
        0.20,
    ),
    Control(
        "employee_training",
        "Практическое обучение сотрудников фишингу и работе с данными",
        "org_legal",
        "preventive",
        24000,
        ["phishing_email", "insider_leak", "pdn_leak"],
        0.24,
        0.15,
        0.00,
    ),
    Control(
        "web_monitoring",
        "Мониторинг сайта, обновлений CMS и форм заявок",
        "technical",
        "detection",
        30000,
        ["website_outage", "account_takeover", "pdn_leak"],
        0.18,
        0.16,
        0.22,
    ),
    Control(
        "reserve_internet_pos",
        "Резервный интернет и сценарий продаж при отказе терминала",
        "economic_management",
        "recovery",
        28000,
        ["pos_outage", "supplier_failure"],
        0.12,
        0.20,
        0.45,
    ),
    Control(
        "supplier_contracts",
        "Договорные SLA и резервные поставщики критичных сервисов",
        "economic_management",
        "preventive",
        45000,
        ["supplier_failure", "website_outage", "pos_outage"],
        0.20,
        0.24,
        0.28,
    ),
    Control(
        "crisis_fund",
        "Резерв затрат на восстановление после ИБ-инцидента",
        "economic_management",
        "recovery",
        80000,
        ["ransomware", "pdn_leak", "website_outage", "supplier_failure"],
        0.00,
        0.34,
        0.18,
    ),
]


QUALITY_LEVELS: dict[str, tuple[str, float]] = {
    "none": ("Мера отсутствует", 0.00),
    "paid": ("Оплачена, но не внедрена", 0.15),
    "formal": ("Внедрена формально", 0.35),
    "working": ("Работает и проверяется", 0.65),
    "embedded": ("Встроена в процесс", 0.90),
}


SECTOR_PROFILES: dict[str, dict[str, float]] = {
    "Розничная торговля": {
        "email": 0.70,
        "website": 0.45,
        "pos": 1.00,
        "crm": 0.65,
        "personal_data": 0.70,
        "cloud": 0.55,
        "bank": 0.85,
        "employees": 0.70,
    },
    "Интернет-магазин": {
        "email": 0.85,
        "website": 1.00,
        "pos": 0.70,
        "crm": 0.90,
        "personal_data": 0.90,
        "cloud": 0.85,
        "bank": 0.80,
        "employees": 0.75,
    },
    "Услуги": {
        "email": 0.80,
        "website": 0.65,
        "pos": 0.75,
        "crm": 0.75,
        "personal_data": 0.80,
        "cloud": 0.65,
        "bank": 0.70,
        "employees": 0.75,
    },
    "B2B-компания": {
        "email": 0.95,
        "website": 0.55,
        "pos": 0.25,
        "crm": 0.90,
        "personal_data": 0.65,
        "cloud": 0.80,
        "bank": 0.85,
        "employees": 0.85,
    },
    "Производство": {
        "email": 0.75,
        "website": 0.45,
        "pos": 0.20,
        "crm": 0.60,
        "personal_data": 0.55,
        "cloud": 0.55,
        "bank": 0.75,
        "employees": 0.80,
    },
    "Медицина / образование": {
        "email": 0.85,
        "website": 0.70,
        "pos": 0.50,
        "crm": 0.75,
        "personal_data": 1.00,
        "cloud": 0.80,
        "bank": 0.65,
        "employees": 0.85,
    },
}
