"""
RFI Field Schema — maps every question in the RFI template to metadata
for extraction, source priority, and Excel positioning.

12 categories, 65 fields. Organized by onboarding workflow.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Source(str, Enum):
    HUBSPOT = "hubspot"
    TRANSCRIPT = "transcript"
    UPLOADED = "uploaded"
    MANUAL = "manual"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MISSING = "missing"


class Category(str, Enum):
    ENGAGEMENT = "Engagement & Project Details"
    COMPANY = "Company Overview"
    CURRENT_STATE = "Current IT State & Provider"
    LICENSING = "Microsoft 365 & Licensing"
    SERVERS = "Servers & Infrastructure"
    DATA = "Data, Files & Applications"
    EMAIL = "Email & Communication"
    NETWORK = "Network & Connectivity"
    DEVICES = "Devices & Endpoints"
    SECURITY = "Security & Compliance"
    BACKUP = "Backup & Disaster Recovery"
    DOCUMENTATION = "Documentation & Handoff"


@dataclass
class RFIField:
    row: int                          # 1-indexed Excel row
    question: str                     # The RFI question text
    category: Category
    key: str                          # Short identifier for this field
    extraction_hint: str              # What to look for in transcripts
    primary_sources: list[Source] = field(default_factory=lambda: [Source.TRANSCRIPT])
    hubspot_property: str | None = None  # Direct HubSpot field if applicable


# ═══════════════════════════════════════════════════════════════════════
# Row layout:
#   Row 1 = document header
#   Each category: 1 header row + N data rows
#   Total: 1 + 12 headers + 65 data = 78 rows
# ═══════════════════════════════════════════════════════════════════════

RFI_FIELDS: list[RFIField] = [

    # ── 1. Engagement & Project Details (rows 3-10, 8 fields) ────────
    # Row 2 = category header
    RFIField(
        row=3, key="bellwether_team",
        question="Who is the Account Team?",
        category=Category.ENGAGEMENT,
        extraction_hint="Manual entry only",
        primary_sources=[Source.MANUAL],
    ),
    RFIField(
        row=4, key="number_of_users",
        question="Number of Users?",
        category=Category.ENGAGEMENT,
        extraction_hint="Manual entry only",
        primary_sources=[Source.MANUAL],
    ),
    RFIField(
        row=5, key="number_of_devices",
        question="Number of Machines?",
        category=Category.ENGAGEMENT,
        extraction_hint="Manual entry only",
        primary_sources=[Source.MANUAL],
    ),
    RFIField(
        row=6, key="main_contact_name",
        question="Primary client contact name?",
        category=Category.ENGAGEMENT,
        extraction_hint="Main point of contact, primary contact, IT contact, decision maker name",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="main_contact_name",
    ),
    RFIField(
        row=7, key="main_contact_email",
        question="Primary client contact email?",
        category=Category.ENGAGEMENT,
        extraction_hint="Contact email address",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="main_contact_email",
    ),
    RFIField(
        row=8, key="main_contact_phone",
        question="Primary client contact phone?",
        category=Category.ENGAGEMENT,
        extraction_hint="Contact phone number",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="main_contact_phone",
    ),
    RFIField(
        row=9, key="contract_type",
        question="What type of contract? (Fully Managed / Infrastructure / Service Desk / Security)",
        category=Category.ENGAGEMENT,
        extraction_hint="Manual entry only",
        primary_sources=[Source.MANUAL],
    ),
    RFIField(
        row=10, key="desired_go_live",
        question="Desired go-live date?",
        category=Category.ENGAGEMENT,
        extraction_hint="Go-live date, start date, launch date, target date, when do they want to start. Go-live = when we begin supporting them. Onboarding starts ~30 days before go-live",
        primary_sources=[Source.HUBSPOT, Source.TRANSCRIPT],
        hubspot_property="closedate",
    ),

    # ── 2. Company Overview (rows 12-16, 5 fields) ──────────────────
    # Row 11 = category header
    RFIField(
        row=12, key="company_name",
        question="What is the name of the company?",
        category=Category.COMPANY,
        extraction_hint="Company name, legal entity name, DBA names",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="name",
    ),
    RFIField(
        row=13, key="company_location",
        question="Where is the company located? List HQ and any remote/satellite/additional offices.",
        category=Category.COMPANY,
        extraction_hint="List headquarters location and all remote, satellite, or additional offices. Include city/state for each. Look for branch offices, retail locations, restaurants, warehouses, field offices",
        primary_sources=[Source.HUBSPOT, Source.TRANSCRIPT],
        hubspot_property="city",
    ),
    RFIField(
        row=14, key="industry_vertical",
        question="Details about this company",
        category=Category.COMPANY,
        extraction_hint="Any relevant details an MSP onboarding team would care about: industry, vertical, what the company does, products/services, number of locations, business model, seasonal patterns, compliance-sensitive verticals (healthcare, legal, finance), operational complexity",
        primary_sources=[Source.TRANSCRIPT],
    ),
    RFIField(
        row=15, key="users_by_location",
        question="Breakdown of users by location (include remote/hybrid workers)?",
        category=Category.COMPANY,
        extraction_hint="User count per office, per location, per branch, per restaurant, corporate vs field. Include remote work policy, hybrid, onsite only, work from home, percentage remote vs onsite",
    ),
    RFIField(
        row=16, key="pain_points",
        question="What are specific challenges or pain points in the current IT setup?",
        category=Category.COMPANY,
        extraction_hint="IT frustrations, issues, problems, slow response, outages, security incidents, ransomware, vendor complaints",
    ),

    # ── 3. Current IT State & Provider (rows 18-21, 4 fields) ────────
    # Row 17 = category header
    RFIField(
        row=18, key="current_support",
        question="Who is the incumbent provider and what is the current scope of services?",
        category=Category.CURRENT_STATE,
        extraction_hint="Current MSP name, incumbent provider, scope of services, what they manage, support tier, SLA, response time, support hours, contract type",
    ),
    RFIField(
        row=19, key="existing_rmm_psa",
        question="What RMM/PSA agents are currently deployed?",
        category=Category.CURRENT_STATE,
        extraction_hint="RMM tool, PSA, ConnectWise, Datto RMM, NinjaRMM, Kaseya, Atera, Autotask, monitoring agents, remote management agents",
    ),
    RFIField(
        row=20, key="other_support_requirements",
        question="Are there any other support requirements we should be aware of?",
        category=Category.CURRENT_STATE,
        extraction_hint="Special support needs, VIP users, executive support, after-hours, weekend support, on-call",
    ),
    RFIField(
        row=21, key="business_hours",
        question="What are the operating hours (Business Hours)?",
        category=Category.CURRENT_STATE,
        extraction_hint="Business hours, operating hours, office hours, 9-5, time zone, shifts. If not explicitly stated, infer from industry context (e.g. restaurants often operate evenings/weekends, law firms standard business hours). When inferring, note 'Estimated based on industry' in the answer",
    ),

    # ── 4. Microsoft 365 & Licensing (rows 23-28, 6 fields) ─────────
    # Row 22 = category header
    RFIField(
        row=23, key="ms_licensing",
        question="What Microsoft licensing is in use? List each license type and qty (include add-ons).",
        category=Category.LICENSING,
        extraction_hint="List each Microsoft license by name and quantity, e.g. 'M365 Business Premium x 40, E3 x 10'. Look for Office 365, Microsoft 365, E1, E3, E5, F1, F3, Business Basic, Business Standard, Business Premium, Exchange Online, any per-user license counts. Also include add-on licenses: MS Phone System, Teams Room, shared mailboxes, Exchange Online Plan, kiosk licenses",
    ),
    RFIField(
        row=24, key="ms_contract_term",
        question="What is the Microsoft licensing contract term? Annual/Monthly? When does the contract end?",
        category=Category.LICENSING,
        extraction_hint="Microsoft contract term, annual vs monthly, renewal date, contract expiration, EA agreement",
    ),
    RFIField(
        row=25, key="ms_tenants",
        question="How many Microsoft Tenants? Why are there multiple tenants?",
        category=Category.LICENSING,
        extraction_hint="Number of tenants, multiple tenants, tenant migration, tenant consolidation, why separate tenants",
    ),
    RFIField(
        row=26, key="ms_licensing_vendor",
        question="Who do they purchase Microsoft licenses from?",
        category=Category.LICENSING,
        extraction_hint="License vendor, CSP, Pax8, Sherweb, Ingram, direct from Microsoft, licensing partner, who sells them licenses",
    ),
    RFIField(
        row=27, key="google_licensing",
        question="What Google Workspace licensing is in use? Qty?",
        category=Category.LICENSING,
        extraction_hint="Google Workspace plan, Business Starter, Standard, Plus, Enterprise, Gmail, Google Drive",
    ),
    RFIField(
        row=28, key="third_party_licensing",
        question="Is there any other 3rd party licensing provided by the current MSP?",
        category=Category.LICENSING,
        extraction_hint="Adobe, EDR, Mimecast, antivirus, backup software, line of business apps provided by MSP",
    ),

    # ── 5. Servers & Infrastructure (rows 30-34, 5 fields) ───────────
    # Row 29 = category header
    RFIField(
        row=30, key="server_hosting",
        question="Where are servers hosted? (onsite, colo, cloud — list each)",
        category=Category.SERVERS,
        extraction_hint="Server location, on-premises, data center, colocation, colo, cloud hosted, hybrid, offsite hosting facility, Azure, AWS, GCP, cloud VMs, IaaS, public cloud. List all locations including equipment at colo or hosting facilities",
    ),
    RFIField(
        row=31, key="server_inventory",
        question="How many servers (physical/virtual/cloud) and what are their roles?",
        category=Category.SERVERS,
        extraction_hint="Number of servers, physical vs virtual, VM count, server inventory, server roles, domain controller, file server, print server, application server, database server, AD, DNS, DHCP, cloud server count, cloud VM roles, what runs in the cloud",
    ),
    RFIField(
        row=32, key="server_specs",
        question="What are the server specs (CPU, RAM, Disk Space)?",
        category=Category.SERVERS,
        extraction_hint="CPU, RAM, disk space, storage, server hardware brand/model, Dell, HP, Lenovo, server specs",
    ),
    RFIField(
        row=33, key="virtualization",
        question="What virtualization technology is used (e.g., VMware, Hyper-V)?",
        category=Category.SERVERS,
        extraction_hint="VMware, Hyper-V, ESXi, vSphere, virtualization platform, hypervisor",
    ),
    RFIField(
        row=34, key="server_ownership",
        question="Who owns the hardware? Any leased/rented equipment to return?",
        category=Category.SERVERS,
        extraction_hint="Server ownership, who owns the hardware, leased vs owned, MSP-owned, client-owned, rented equipment, leased hardware, equipment to return, lease expiration",
    ),

    # ── 6. Data, Files & Applications (rows 36-39, 4 fields) ────────
    # Row 35 = category header
    RFIField(
        row=36, key="file_repository",
        question="File repository location?",
        category=Category.DATA,
        extraction_hint="File storage, file server, SharePoint, OneDrive, Dropbox, Google Drive, NAS, network drive, mapped drives",
    ),
    RFIField(
        row=37, key="data_size_migration",
        question="How much data and how much needs migrating?",
        category=Category.DATA,
        extraction_hint="Data size, total storage, terabytes, gigabytes, how much data, data migration volume, what needs to move, migration scope",
    ),
    RFIField(
        row=38, key="applications",
        question="What applications are in use? (LOB, SaaS, standard desktop)",
        category=Category.DATA,
        extraction_hint="LOB apps, line of business, industry software, ERP, CRM, accounting, QuickBooks, Great Plains, POS, Toast, Aloha, critical applications, 3rd party apps, SaaS apps, Salesforce, HubSpot, Slack, Zoom, Asana, Monday, cloud applications, software subscriptions, standard apps, SOE, standard operating environment, installed applications, business apps",
    ),
    RFIField(
        row=39, key="lob_app_vendor_contacts",
        question="Who are the vendor contacts for critical LOB applications?",
        category=Category.DATA,
        extraction_hint="App vendor contact, vendor support number, vendor account rep, application vendor relationship",
    ),

    # ── 7. Email & Communication (rows 41-47, 7 fields) ─────────────
    # Row 40 = category header
    RFIField(
        row=41, key="email_hosting_migration",
        question="Where is email hosted and will migration be needed?",
        category=Category.EMAIL,
        extraction_hint="Email platform, Office 365, Google Workspace, Exchange Online, Exchange Server, GoDaddy, email hosting, email migration, tenant migration, email move, mailbox migration, tenant-to-tenant",
    ),
    RFIField(
        row=42, key="mailbox_inventory",
        question="How many mailboxes (user/shared)? Any public folders?",
        category=Category.EMAIL,
        extraction_hint="Number of mailboxes, user mailboxes, shared mailboxes, mailbox count, email accounts, public folders, Exchange public folders, shared folders",
    ),
    RFIField(
        row=43, key="email_security",
        question="What Email Security is in place? IE. Proofpoint, Mimecast, Defender for Office 365",
        category=Category.EMAIL,
        extraction_hint="Email security, Proofpoint, Mimecast, Defender for Office 365, email filtering, spam filter, phishing protection",
    ),
    RFIField(
        row=44, key="number_of_domains",
        question="How many domains?",
        category=Category.EMAIL,
        extraction_hint="Number of email domains, domain count, vanity domains, domain names",
    ),
    RFIField(
        row=45, key="domain_website_hosting",
        question="Who manages DNS, domain registration, and website hosting?",
        category=Category.EMAIL,
        extraction_hint="DNS provider, domain registrar, GoDaddy, Cloudflare, website hosting, who manages the domain, DNS management, website host",
    ),
    RFIField(
        row=46, key="collaboration_tools",
        question="What collaboration tools are in use for communication and file sharing?",
        category=Category.EMAIL,
        extraction_hint="Teams, Slack, Zoom, SharePoint, OneDrive, Dropbox, Google Drive, collaboration tools",
    ),
    RFIField(
        row=47, key="phone_system",
        question="Current phone system and any plans to change?",
        category=Category.EMAIL,
        extraction_hint="Phone system, PBX, VoIP, Teams Phone, RingCentral, 8x8, Cisco, desk phones, softphone, phone upgrade, new phone system, migrate phone, phone replacement, Teams calling",
    ),

    # ── 8. Network & Connectivity (rows 49-54, 6 fields) ────────────
    # Row 48 = category header
    RFIField(
        row=49, key="internet_connectivity",
        question="Internet provider/speed — who manages the relationship?",
        category=Category.NETWORK,
        extraction_hint="ISP, internet provider, bandwidth, speed, fiber, cable, Comcast, AT&T, Mbps, Gbps, ISP management, who manages internet, ISP account, ISP billing, internet vendor relationship",
    ),
    RFIField(
        row=50, key="firewalls",
        question="Number of firewalls and the brand/model(s)?",
        category=Category.NETWORK,
        extraction_hint="Firewall count, firewall brand/model, SonicWall, Fortinet, FortiGate, Meraki, Mako, Palo Alto, WatchGuard, Cisco, end of life firewall. Include brand/model even if mentioned alongside switches or other equipment",
    ),
    RFIField(
        row=51, key="network_equipment",
        question="Network equipment: routers, switches, WAPs (brand/model and count)",
        category=Category.NETWORK,
        extraction_hint="Router count, router brand/model, Cisco, Meraki, Mako, Ubiquiti, switch count, switch brand/model, HP, managed switch, PoE, wireless access points, WAP count, WAP brand/model, Aruba, Wi-Fi, WiFi. Include brand/model even if mentioned alongside firewalls or other equipment",
    ),
    RFIField(
        row=52, key="printers_copiers",
        question="What printers/copiers are in the environment? Managed or purchased?",
        category=Category.NETWORK,
        extraction_hint="Printers, copiers, MFP, managed print, print vendor, Ricoh, Canon, HP, Xerox, print service",
    ),
    RFIField(
        row=53, key="network_diagram",
        question="Is there a current Network diagram?",
        category=Category.NETWORK,
        extraction_hint="Network diagram, network map, topology, Visio, network documentation",
    ),
    RFIField(
        row=54, key="other_it_vendors",
        question="Are there existing relationships with other IT vendors or service providers?",
        category=Category.NETWORK,
        extraction_hint="Other IT vendors, ISP, telco, copier vendor, vendor relationships, other providers. Do NOT include firewall, switch, router, or WAP brands here — those belong in the dedicated networking fields",
    ),

    # ── 9. Devices & Endpoints (rows 56-60, 5 fields) ───────────────
    # Row 55 = category header
    RFIField(
        row=56, key="device_inventory",
        question="Device inventory: Windows, macOS, mobile counts. Corporate or BYOD?",
        category=Category.DEVICES,
        extraction_hint="Windows PC count, Windows laptops, Windows desktops, Mac count, MacBooks, iMacs, Apple computers, macOS devices, iPhone count, Android count, iOS devices, mobile phones, corporate phones, personal phones, BYOD mobile, corporate owned, bring your own device, company-issued, personal devices",
    ),
    RFIField(
        row=57, key="domain_join",
        question="What are the Devices joined to (Active Directory/Azure AD/Hybrid Azure Joined)?",
        category=Category.DEVICES,
        extraction_hint="Domain joined, Active Directory, Azure AD, Entra ID, hybrid join, workgroup, domain controller",
    ),
    RFIField(
        row=58, key="device_encryption",
        question="Are the devices Encrypted (Bitlocker, File Vault)?",
        category=Category.DEVICES,
        extraction_hint="BitLocker, FileVault, disk encryption, device encryption, full disk encryption",
    ),
    RFIField(
        row=59, key="heavy_workloads",
        question="Do users process heavy workloads on their devices? What processes are run?",
        category=Category.DEVICES,
        extraction_hint="Heavy workloads, rendering, CAD, video editing, data processing, resource-intensive apps",
    ),
    RFIField(
        row=60, key="asset_register",
        question="Is there an Asset Register or Inventory?",
        category=Category.DEVICES,
        extraction_hint="Asset register, inventory list, CMDB, asset tracking, device inventory, hardware list",
    ),

    # ── 10. Security & Compliance (rows 62-70, 9 fields) ────────────
    # Row 61 = category header
    RFIField(
        row=62, key="cybersecurity_endpoint",
        question="What cybersecurity and endpoint protection is in place?",
        category=Category.SECURITY,
        extraction_hint="Security stack, antivirus, EDR, SIEM, SOC, security tools, firewall, threat detection, endpoint protection, SentinelOne, CrowdStrike, Defender, Webroot, Sophos, Huntress",
    ),
    RFIField(
        row=63, key="identity_management",
        question="What identity management is in place? (MFA, SSO)",
        category=Category.SECURITY,
        extraction_hint="Multi-factor authentication, MFA, 2FA, Azure MFA, Okta, DUO, Authenticator app, SSO, single sign-on, JumpCloud, OneLogin, identity provider, IdP, SAML",
    ),
    RFIField(
        row=64, key="mdm",
        question="Is there a Mobile Device Management (MDM) solution in place? (Windows & Mac)",
        category=Category.SECURITY,
        extraction_hint="MDM, Intune, Mobile Iron, JAMF, Mosyle, mobile device management, device enrollment, Apple MDM, Mac management",
    ),
    RFIField(
        row=65, key="patch_management",
        question="What is the current patch management posture?",
        category=Category.SECURITY,
        extraction_hint="Patch management, Windows updates, WSUS, patching cadence, update policy, third-party patching, patch compliance",
    ),
    RFIField(
        row=66, key="security_awareness_training",
        question="Is security awareness training in place? What platform?",
        category=Category.SECURITY,
        extraction_hint="Security awareness training, KnowBe4, Proofpoint SAT, phishing simulation, security training, cybersecurity training",
    ),
    RFIField(
        row=67, key="cyber_insurance",
        question="Does the company have cyber insurance? Who is the carrier?",
        category=Category.SECURITY,
        extraction_hint="Cyber insurance, cyber liability, insurance carrier, insurance requirements, policy requirements, coverage",
    ),
    RFIField(
        row=68, key="remote_access",
        question="Remote access solutions (VPN, virtual desktops, remote support tools)?",
        category=Category.SECURITY,
        extraction_hint="Remote access, VPN, Citrix, AVD, Azure Virtual Desktop, RDP, remote desktop, WVD, site-to-site VPN, client VPN, VPN concentrator, SSL VPN, IPSec, VPN termination point, remote support tool, ScreenConnect, ConnectWise Control, TeamViewer, Splashtop",
    ),
    RFIField(
        row=69, key="compliance_requirements",
        question="Are there any compliance requirements or industry-specific regulations?",
        category=Category.SECURITY,
        extraction_hint="Compliance, HIPAA, PCI, SOX, GDPR, CMMC, NIST, industry regulations, audit requirements, PCI-DSS",
    ),
    RFIField(
        row=70, key="archiving",
        question="Which archiving vendor? What is being archived? Number of users?",
        category=Category.SECURITY,
        extraction_hint="Archiving vendor, email archive, Bloomberg archive, Teams archive, compliance archiving, retention policy",
    ),

    # ── 11. Backup & Disaster Recovery (rows 72-75, 4 fields) ───────
    # Row 71 = category header
    RFIField(
        row=72, key="backup_solution",
        question="What backup solution is in place? What vendor?",
        category=Category.BACKUP,
        extraction_hint="Backup solution, backup vendor, Veeam, Datto, Acronis, BDR, backup appliance, cloud backup, backup frequency",
    ),
    RFIField(
        row=73, key="disaster_recovery_plan",
        question="Is there a disaster recovery plan? What are the RTO/RPO targets?",
        category=Category.BACKUP,
        extraction_hint="Disaster recovery, DR plan, RTO, RPO, recovery time, recovery point, business continuity, failover",
    ),
    RFIField(
        row=74, key="email_backup",
        question="What backup is in place for email/SaaS data?",
        category=Category.BACKUP,
        extraction_hint="Email backup, SaaS backup, backup for 365, Barracuda, Veeam for 365, Spanning, cloud-to-cloud backup",
    ),
    RFIField(
        row=75, key="backup_equipment_onsite",
        question="Is there any backup equipment on site?",
        category=Category.BACKUP,
        extraction_hint="On-site backup equipment, BDR appliance, NAS, backup server, tape drive, local backup device, Datto appliance, backup hardware on premises",
    ),

    # ── 12. Documentation & Handoff (rows 77-78, 2 fields) ──────────
    # Row 76 = category header
    RFIField(
        row=77, key="existing_documentation",
        question="Is there existing IT documentation? What platform (IT Glue, Passportal, wiki)?",
        category=Category.DOCUMENTATION,
        extraction_hint="IT documentation, IT Glue, Passportal, Hudu, wiki, documentation platform, knowledge base, runbooks",
    ),
    RFIField(
        row=78, key="admin_credentials",
        question="What admin credentials and accounts need to be transferred?",
        category=Category.DOCUMENTATION,
        extraction_hint="Admin credentials, admin accounts, global admin, service accounts, root passwords, credential handoff, password vault",
    ),
]


def get_fields_by_category() -> dict[Category, list[RFIField]]:
    result: dict[Category, list[RFIField]] = {}
    for f in RFI_FIELDS:
        result.setdefault(f.category, []).append(f)
    return result


def get_field_by_key(key: str) -> RFIField | None:
    for f in RFI_FIELDS:
        if f.key == key:
            return f
    return None
