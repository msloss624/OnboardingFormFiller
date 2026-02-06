"""
RFI Field Schema — maps every question in the RFI template to metadata
for extraction, source priority, and Excel positioning.
"""
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
    GENERAL = "General"
    CURRENT_STATE = "Current State"
    MICROSOFT = "Microsoft Licensing"
    GOOGLE = "Google Workspace"
    THIRD_PARTY = "3rd Party Licensing"
    ASSETS = "Asset Management"
    SERVERS_ONPREM = "Servers (On-Prem)"
    SERVERS_CLOUD = "Servers (Cloud)"
    DATA = "Data & Files"
    SECURITY = "Cybersecurity"
    REMOTE_ACCESS = "Remote Access"
    EMAIL = "Email"
    COMPLIANCE = "Compliance"
    DEVICES = "Devices"
    COLLABORATION = "Collaboration"
    NETWORK = "Network"
    PHONE = "Phone"


@dataclass
class RFIField:
    row: int                          # 1-indexed Excel row
    question: str                     # The RFI question text
    category: Category
    key: str                          # Short identifier for this field
    extraction_hint: str              # What to look for in transcripts
    primary_sources: list[Source] = field(default_factory=lambda: [Source.TRANSCRIPT])
    hubspot_property: str | None = None  # Direct HubSpot field if applicable


# All 87 rows of the RFI template. Rows are 1-indexed matching the Excel.
# Row 1 = header, row 2+ = data.
RFI_FIELDS: list[RFIField] = [

    # ── General ──────────────────────────────────────────────────────
    RFIField(
        row=3, key="company_name",
        question="What is the name of the company?",
        category=Category.GENERAL,
        extraction_hint="Company name, legal entity name, DBA names",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="name",
    ),
    RFIField(
        row=4, key="company_location",
        question="Where is the company located (HQ and remote offices)?",
        category=Category.GENERAL,
        extraction_hint="HQ city/state, office locations, remote office addresses, satellite offices",
        primary_sources=[Source.HUBSPOT, Source.TRANSCRIPT],
        hubspot_property="city",
    ),
    RFIField(
        row=5, key="number_of_users",
        question="Number of users?",
        category=Category.GENERAL,
        extraction_hint="Total user count, number of employees using computers, headcount, corporate users vs restaurant/field users",
        primary_sources=[Source.TRANSCRIPT, Source.HUBSPOT],
        hubspot_property="numberofemployees",
    ),
    RFIField(
        row=6, key="onsite_or_remote",
        question="Are users working onsite or remotely?",
        category=Category.GENERAL,
        extraction_hint="Remote work policy, hybrid, onsite only, work from home, percentage remote vs onsite",
    ),
    RFIField(
        row=7, key="users_by_location",
        question="Breakdown of users by locations?",
        category=Category.GENERAL,
        extraction_hint="User count per office, per location, per branch, per restaurant, corporate vs field",
    ),
    RFIField(
        row=8, key="number_of_devices",
        question="Number of end-user devices?",
        category=Category.GENERAL,
        extraction_hint="Total device count, laptops, desktops, number of machines, workstations",
    ),
    RFIField(
        row=9, key="pain_points",
        question="What are specific challenges or pain points in the current IT setup?",
        category=Category.GENERAL,
        extraction_hint="IT frustrations, issues, problems, slow response, outages, security incidents, ransomware, vendor complaints",
    ),

    # ── Current State ────────────────────────────────────────────────
    RFIField(
        row=11, key="current_support",
        question="What is the current support type, quantity, and cadence?",
        category=Category.CURRENT_STATE,
        extraction_hint="Current MSP name, support tier, SLA, response time, support hours, contract type, per-user pricing",
    ),
    RFIField(
        row=12, key="other_support_requirements",
        question="Are there any other support requirements we should be aware of?",
        category=Category.CURRENT_STATE,
        extraction_hint="Special support needs, VIP users, executive support, after-hours, weekend support, on-call",
    ),
    RFIField(
        row=13, key="ticket_stats",
        question="Stats for number of support tickets/types per month for the past 6 months? Peak/Off-Peak?",
        category=Category.CURRENT_STATE,
        extraction_hint="Ticket volume, tickets per month, peak periods, busy seasons, common ticket types",
    ),
    RFIField(
        row=14, key="business_hours",
        question="What is the operating hours (Business Hours)?",
        category=Category.CURRENT_STATE,
        extraction_hint="Business hours, operating hours, office hours, 9-5, time zone, shifts",
    ),

    # ── Microsoft Licensing ──────────────────────────────────────────
    RFIField(
        row=16, key="ms_licensing",
        question="What Microsoft licensing is in use? Qty?",
        category=Category.MICROSOFT,
        extraction_hint="Microsoft 365 plan, Office 365 license type, E3, E5, Business Premium, Business Basic, license count, per-user licensing",
    ),
    RFIField(
        row=17, key="ms_additional_licensing",
        question="Are there any additional Microsoft licensing? Qty?",
        category=Category.MICROSOFT,
        extraction_hint="MS Phone System, Teams Room, shared mailboxes, Exchange Online Plan, add-on licenses, kiosk licenses",
    ),
    RFIField(
        row=18, key="ms_contract_term",
        question="What is the Microsoft licensing contract term? Annual/Monthly? When does the contract end?",
        category=Category.MICROSOFT,
        extraction_hint="Microsoft contract term, annual vs monthly, renewal date, contract expiration, EA agreement",
    ),
    RFIField(
        row=19, key="ms_tenants",
        question="How many Microsoft Tenants? Why are there multiple tenants?",
        category=Category.MICROSOFT,
        extraction_hint="Number of tenants, multiple tenants, tenant migration, tenant consolidation, why separate tenants",
    ),

    # ── Google Workspace ─────────────────────────────────────────────
    RFIField(
        row=21, key="google_licensing",
        question="What Google Workspace Licencing is in use? Qty?",
        category=Category.GOOGLE,
        extraction_hint="Google Workspace plan, Business Starter, Standard, Plus, Enterprise, Gmail, Google Drive",
    ),

    # ── 3rd Party Licensing ──────────────────────────────────────────
    RFIField(
        row=22, key="third_party_licensing",
        question="Is there any other 3rd party licencing that is provided by the current MSP?",
        category=Category.THIRD_PARTY,
        extraction_hint="Adobe, EDR, Mimecast, antivirus, backup software, line of business apps provided by MSP",
    ),

    # ── Asset Management ─────────────────────────────────────────────
    RFIField(
        row=24, key="asset_register",
        question="Is there an Asset Register or Inventory?",
        category=Category.ASSETS,
        extraction_hint="Asset register, inventory list, CMDB, asset tracking, device inventory, hardware list",
    ),

    # ── Servers (On-Prem) ────────────────────────────────────────────
    RFIField(
        row=26, key="server_location",
        question="Where are the servers hosted? Onsite, data center/co-lo, or cloud-based?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="Server location, on-premises, data center, colocation, colo, cloud hosted, hybrid",
    ),
    RFIField(
        row=27, key="server_count",
        question="How many servers are there? How many are physical? How many are virtual?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="Number of servers, physical vs virtual, VM count, server inventory",
    ),
    RFIField(
        row=28, key="server_roles",
        question="What are the server roles?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="Server roles, domain controller, file server, print server, application server, database server, AD, DNS, DHCP",
    ),
    RFIField(
        row=29, key="server_specs",
        question="What are the server specs (CPU, RAM, Disk Space)?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="CPU, RAM, disk space, storage, server hardware model, Dell, HP, Lenovo, server specs",
    ),
    RFIField(
        row=30, key="virtualization",
        question="What virtualization technology is used (e.g., VMware, Hyper-V)?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="VMware, Hyper-V, ESXi, vSphere, virtualization platform, hypervisor",
    ),
    RFIField(
        row=31, key="server_ownership",
        question="Who owns the physical servers? Data center/colo servers? Cloud servers?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="Server ownership, who owns the hardware, leased vs owned, MSP-owned, client-owned",
    ),
    RFIField(
        row=32, key="disaster_recovery",
        question="Do you have a disaster recovery plan or backup system in place? Which vendor?",
        category=Category.SERVERS_ONPREM,
        extraction_hint="Disaster recovery, DR plan, backup solution, backup vendor, Veeam, Datto, Acronis, BDR, RTO, RPO",
    ),

    # ── Servers (Cloud) ──────────────────────────────────────────────
    RFIField(
        row=34, key="cloud_servers",
        question="Are there Public Cloud Servers (Azure/AWS)?",
        category=Category.SERVERS_CLOUD,
        extraction_hint="Azure, AWS, GCP, cloud VMs, cloud servers, IaaS, public cloud",
    ),
    RFIField(
        row=35, key="cloud_server_roles",
        question="How many servers are there what are their roles?",
        category=Category.SERVERS_CLOUD,
        extraction_hint="Cloud server count, cloud VM roles, what runs in the cloud",
    ),

    # ── Data & Files ─────────────────────────────────────────────────
    RFIField(
        row=37, key="file_repository",
        question="File repository location",
        category=Category.DATA,
        extraction_hint="File storage, file server, SharePoint, OneDrive, Dropbox, Google Drive, NAS, network drive, mapped drives",
    ),
    RFIField(
        row=38, key="total_data_size",
        question="What is total size of data?",
        category=Category.DATA,
        extraction_hint="Data size, total storage, terabytes, gigabytes, how much data",
    ),
    RFIField(
        row=39, key="data_migration",
        question="How much data needs to be migrated?",
        category=Category.DATA,
        extraction_hint="Data migration volume, what needs to move, migration scope",
    ),
    RFIField(
        row=40, key="linked_files",
        question="Are there linked files in spreadsheets?",
        category=Category.DATA,
        extraction_hint="Linked spreadsheets, Excel links, external references, shared workbooks, linked files",
    ),
    RFIField(
        row=41, key="third_party_apps",
        question="Are there any 3rd party applications that need to be considered?",
        category=Category.DATA,
        extraction_hint="Line of business apps, LOB apps, industry software, ERP, CRM, accounting software, QuickBooks, Great Plains, POS, Toast, Aloha",
    ),

    # ── Cybersecurity ────────────────────────────────────────────────
    RFIField(
        row=43, key="cybersecurity_measures",
        question="What cybersecurity measures do you currently have in place?",
        category=Category.SECURITY,
        extraction_hint="Security stack, antivirus, EDR, SIEM, SOC, security tools, firewall, threat detection",
    ),
    RFIField(
        row=44, key="mfa",
        question="What MFA is in place? IE. Azure, Okta, DUO",
        category=Category.SECURITY,
        extraction_hint="Multi-factor authentication, MFA, 2FA, Azure MFA, Okta, DUO, Authenticator app",
    ),
    RFIField(
        row=45, key="mdm",
        question="Is there a Mobile Device Management (MDM) solution in place? IE. Intune, Mobile Iron",
        category=Category.SECURITY,
        extraction_hint="MDM, Intune, Mobile Iron, JAMF, mobile device management, device enrollment",
    ),
    RFIField(
        row=46, key="mdm_macos",
        question="Is there different MDM software in place for MacOS?",
        category=Category.SECURITY,
        extraction_hint="Mac MDM, JAMF, Mosyle, Mac management, Apple device management",
    ),
    RFIField(
        row=47, key="endpoint_protection",
        question="What endpoint protection is in place?",
        category=Category.SECURITY,
        extraction_hint="Endpoint protection, EDR, antivirus, SentinelOne, CrowdStrike, Defender, Webroot, Sophos, Huntress",
    ),

    # ── Remote Access ────────────────────────────────────────────────
    RFIField(
        row=49, key="remote_access",
        question="What is remote access solutions? IE. VPN, Citrix, Azure Virtual Desktop",
        category=Category.REMOTE_ACCESS,
        extraction_hint="Remote access, VPN, Citrix, AVD, Azure Virtual Desktop, RDP, remote desktop, WVD",
    ),
    RFIField(
        row=50, key="vpn",
        question="Is there a client VPN? Where is the VPN terminating and type of VPN?",
        category=Category.REMOTE_ACCESS,
        extraction_hint="VPN type, site-to-site VPN, client VPN, VPN concentrator, SSL VPN, IPSec, VPN termination point",
    ),
    RFIField(
        row=51, key="remote_pc_access",
        question="Do users need remote access to PCs in the office?",
        category=Category.REMOTE_ACCESS,
        extraction_hint="Remote into office PC, remote desktop, RDP to office, access office computer from home",
    ),

    # ── Email ────────────────────────────────────────────────────────
    RFIField(
        row=53, key="email_hosting",
        question="Where is email hosted? Office 365/Google/Exchange Server/GoDaddy/etc?",
        category=Category.EMAIL,
        extraction_hint="Email platform, Office 365, Google Workspace, Exchange Online, Exchange Server, GoDaddy, email hosting",
    ),
    RFIField(
        row=54, key="email_migration",
        question="Do emails need to be migrated?",
        category=Category.EMAIL,
        extraction_hint="Email migration, tenant migration, email move, mailbox migration, tenant-to-tenant",
    ),
    RFIField(
        row=55, key="mailbox_count",
        question="How many mailboxes need to be migrated? User & shared",
        category=Category.EMAIL,
        extraction_hint="Number of mailboxes, user mailboxes, shared mailboxes, mailbox count, email accounts",
    ),
    RFIField(
        row=56, key="public_folders",
        question="Are there Public Folders?",
        category=Category.EMAIL,
        extraction_hint="Public folders, Exchange public folders, shared folders",
    ),
    RFIField(
        row=57, key="email_security",
        question="What Email Security is in place? IE. Proofpoint, Mimecast, Defender for Office 365",
        category=Category.EMAIL,
        extraction_hint="Email security, Proofpoint, Mimecast, Defender for Office 365, email filtering, spam filter, phishing protection",
    ),
    RFIField(
        row=58, key="number_of_domains",
        question="How many domains?",
        category=Category.EMAIL,
        extraction_hint="Number of email domains, domain count, vanity domains, domain names",
    ),
    RFIField(
        row=59, key="email_backup",
        question="What backup is in place for email?",
        category=Category.EMAIL,
        extraction_hint="Email backup, email archiving, backup for 365, Barracuda, Veeam for 365, SaaS backup",
    ),

    # ── Compliance ───────────────────────────────────────────────────
    RFIField(
        row=61, key="compliance_requirements",
        question="Are there any compliance requirements or industry-specific regulations you need to adhere to?",
        category=Category.COMPLIANCE,
        extraction_hint="Compliance, HIPAA, PCI, SOX, GDPR, CMMC, NIST, industry regulations, audit requirements, PCI-DSS for restaurants",
    ),
    RFIField(
        row=62, key="archiving",
        question="Which vendor? What is being archived? Number of users?",
        category=Category.COMPLIANCE,
        extraction_hint="Archiving vendor, email archive, Bloomberg archive, Teams archive, compliance archiving, retention policy",
    ),

    # ── Devices ──────────────────────────────────────────────────────
    RFIField(
        row=64, key="windows_devices",
        question="Number of windows devices",
        category=Category.DEVICES,
        extraction_hint="Windows PC count, Windows laptops, Windows desktops, Windows device inventory",
    ),
    RFIField(
        row=65, key="macos_devices",
        question="Number of macOS devices",
        category=Category.DEVICES,
        extraction_hint="Mac count, MacBooks, iMacs, Apple computers, macOS devices",
    ),
    RFIField(
        row=66, key="device_ownership",
        question="Are devices corporate owned or BYOD?",
        category=Category.DEVICES,
        extraction_hint="Corporate owned, BYOD, bring your own device, company-issued, personal devices",
    ),
    RFIField(
        row=67, key="iphone_count",
        question="Number of iPhone mobile devices (Corporate/Personal)",
        category=Category.DEVICES,
        extraction_hint="iPhone count, iOS devices, corporate iPhones, personal iPhones",
    ),
    RFIField(
        row=68, key="android_count",
        question="Number of Android mobile devices (Corporate/Personal)",
        category=Category.DEVICES,
        extraction_hint="Android count, Android phones, Samsung, corporate Android, personal Android",
    ),
    RFIField(
        row=69, key="domain_join",
        question="What are the Devices joined to (Active Directory/Azure AD/Hybrid Azure Joined)?",
        category=Category.DEVICES,
        extraction_hint="Domain joined, Active Directory, Azure AD, Entra ID, hybrid join, workgroup, domain controller",
    ),
    RFIField(
        row=70, key="standard_apps",
        question="Do you have a standard set of applications used across the organization? What are the apps?",
        category=Category.DEVICES,
        extraction_hint="Standard apps, standard software, SOE, standard operating environment, installed applications, business apps",
    ),
    RFIField(
        row=71, key="device_encryption",
        question="Are the devices Encrypted (Bitlocker, File Vault)?",
        category=Category.DEVICES,
        extraction_hint="BitLocker, FileVault, disk encryption, device encryption, full disk encryption",
    ),
    RFIField(
        row=72, key="heavy_workloads",
        question="Do users process heavy workloads on their devices, what processes are run?",
        category=Category.DEVICES,
        extraction_hint="Heavy workloads, rendering, CAD, video editing, data processing, resource-intensive apps",
    ),
    RFIField(
        row=73, key="critical_apps",
        question="Are there any critical applications or software solutions specific to the industry?",
        category=Category.DEVICES,
        extraction_hint="Industry-specific software, POS systems, EHR, legal software, accounting software, Toast, Aloha, Great Plains, QuickBooks",
    ),
    RFIField(
        row=74, key="collaboration_tools",
        question="What collaboration tools are in use for communication and file sharing?",
        category=Category.COLLABORATION,
        extraction_hint="Teams, Slack, Zoom, SharePoint, OneDrive, Dropbox, Google Drive, collaboration tools",
    ),

    # ── Network ──────────────────────────────────────────────────────
    RFIField(
        row=77, key="internet_connectivity",
        question="What internet connectivity is in place (Provider/Speed)?",
        category=Category.NETWORK,
        extraction_hint="ISP, internet provider, bandwidth, speed, fiber, cable, Comcast, AT&T, Mbps, Gbps",
    ),
    RFIField(
        row=78, key="firewalls",
        question="Number of firewalls and the model(s)",
        category=Category.NETWORK,
        extraction_hint="Firewall count, firewall model, SonicWall, Fortinet, FortiGate, Meraki, Palo Alto, WatchGuard, Cisco, end of life firewall",
    ),
    RFIField(
        row=79, key="routers",
        question="Number of routers and the model(s)",
        category=Category.NETWORK,
        extraction_hint="Router count, router model, Cisco, Meraki, Ubiquiti, routing",
    ),
    RFIField(
        row=80, key="switches",
        question="Number of switches and the model(s)",
        category=Category.NETWORK,
        extraction_hint="Switch count, switch model, Cisco, Meraki, Ubiquiti, HP, managed switch, PoE",
    ),
    RFIField(
        row=81, key="waps",
        question="Number of WAPs and the model(s)",
        category=Category.NETWORK,
        extraction_hint="Wireless access points, WAP count, WAP model, Meraki, Ubiquiti, Aruba, Wi-Fi, WiFi",
    ),
    RFIField(
        row=82, key="network_diagram",
        question="Is there a current Network diagram?",
        category=Category.NETWORK,
        extraction_hint="Network diagram, network map, topology, Visio, network documentation",
    ),
    RFIField(
        row=83, key="other_it_vendors",
        question="Are there existing relationships with other IT vendors or service providers?",
        category=Category.NETWORK,
        extraction_hint="Other IT vendors, ISP, telco, copier vendor, vendor relationships, other providers, Mako",
    ),

    # ── Phone ────────────────────────────────────────────────────────
    RFIField(
        row=85, key="phone_system",
        question="What is the current phone system?",
        category=Category.PHONE,
        extraction_hint="Phone system, PBX, VoIP, Teams Phone, RingCentral, 8x8, Cisco, desk phones, softphone",
    ),
    RFIField(
        row=86, key="phone_upgrade",
        question="Are you looking to change or upgrade the phone system?",
        category=Category.PHONE,
        extraction_hint="Phone upgrade, new phone system, migrate phone, phone replacement, Teams calling",
    ),
    RFIField(
        row=87, key="voice_recording",
        question="Is there Voice Recording in place and is it required? What system is in place and where is it stored?",
        category=Category.PHONE,
        extraction_hint="Voice recording, call recording, compliance recording, recording storage",
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
