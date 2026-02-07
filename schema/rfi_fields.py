"""
RFI Field Schema — maps every question in the RFI template to metadata
for extraction, source priority, and Excel positioning.

12 categories, 92 fields. Organized by onboarding workflow.
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
#   Total: 1 + 12 headers + 92 data = 105 rows
# ═══════════════════════════════════════════════════════════════════════

RFI_FIELDS: list[RFIField] = [

    # ── 1. Engagement & Project Details ──────────────────────────────
    # Row 2 = category header
    RFIField(
        row=3, key="bellwether_team",
        question="Who is the Account Team?",
        category=Category.ENGAGEMENT,
        extraction_hint="Bellwether account team, AE, Technical Advisor, account executive, sales engineer",
        primary_sources=[Source.MANUAL],
        hubspot_property="deal_owner",
    ),
    RFIField(
        row=4, key="number_of_users",
        question="Number of Users?",
        category=Category.ENGAGEMENT,
        extraction_hint="Total user count, number of employees using computers, headcount, corporate users vs restaurant/field users",
        primary_sources=[Source.MANUAL, Source.HUBSPOT],
        hubspot_property="numberofemployees",
    ),
    RFIField(
        row=5, key="number_of_devices",
        question="Number of Machines?",
        category=Category.ENGAGEMENT,
        extraction_hint="Total device count, laptops, desktops, number of machines, workstations",
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
        question="What type of contract? (BPM / Infra Only / SD Only / Security Only)",
        category=Category.ENGAGEMENT,
        extraction_hint="Contract type, BPM, business process management, infrastructure only, service desk only, security only, managed services scope",
        primary_sources=[Source.TRANSCRIPT, Source.MANUAL],
    ),
    RFIField(
        row=10, key="desired_go_live",
        question="Desired go-live date?",
        category=Category.ENGAGEMENT,
        extraction_hint="Go-live date, start date, launch date, target date, when do they want to start",
        primary_sources=[Source.HUBSPOT, Source.TRANSCRIPT],
        hubspot_property="closedate",
    ),
    RFIField(
        row=11, key="transition_timeline",
        question="What is the transition/overlap period with the current provider?",
        category=Category.ENGAGEMENT,
        extraction_hint="Transition period, overlap, handoff timeline, notice period, contract end date with current MSP, runbook period",
        primary_sources=[Source.TRANSCRIPT],
    ),

    # ── 2. Company Overview ─────────────────────────────────────────
    # Row 12 = category header
    RFIField(
        row=13, key="company_name",
        question="What is the name of the company?",
        category=Category.COMPANY,
        extraction_hint="Company name, legal entity name, DBA names",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="name",
    ),
    RFIField(
        row=14, key="company_location",
        question="Where is the company located (HQ and remote offices)?",
        category=Category.COMPANY,
        extraction_hint="HQ city/state, office locations, remote office addresses, satellite offices",
        primary_sources=[Source.HUBSPOT, Source.TRANSCRIPT],
        hubspot_property="city",
    ),
    RFIField(
        row=15, key="industry_vertical",
        question="What industry/vertical is the company in?",
        category=Category.COMPANY,
        extraction_hint="Industry, vertical, sector, restaurant, healthcare, legal, financial, manufacturing, retail",
        primary_sources=[Source.HUBSPOT],
        hubspot_property="industry",
    ),
    RFIField(
        row=16, key="onsite_or_remote",
        question="Are users working onsite or remotely?",
        category=Category.COMPANY,
        extraction_hint="Remote work policy, hybrid, onsite only, work from home, percentage remote vs onsite",
    ),
    RFIField(
        row=17, key="users_by_location",
        question="Breakdown of users by locations?",
        category=Category.COMPANY,
        extraction_hint="User count per office, per location, per branch, per restaurant, corporate vs field",
    ),
    RFIField(
        row=18, key="pain_points",
        question="What are specific challenges or pain points in the current IT setup?",
        category=Category.COMPANY,
        extraction_hint="IT frustrations, issues, problems, slow response, outages, security incidents, ransomware, vendor complaints",
    ),

    # ── 3. Current IT State & Provider ──────────────────────────────
    # Row 19 = category header
    RFIField(
        row=20, key="current_support",
        question="What is the current support type, quantity, and cadence?",
        category=Category.CURRENT_STATE,
        extraction_hint="Current MSP name, support tier, SLA, response time, support hours, contract type, per-user pricing",
    ),
    RFIField(
        row=21, key="msp_cooperation",
        question="Is the outgoing MSP cooperative with the transition?",
        category=Category.CURRENT_STATE,
        extraction_hint="Outgoing MSP cooperation, transition support, data handoff, hostile MSP, willing to help, responsive, unresponsive, holding data hostage",
    ),
    RFIField(
        row=22, key="existing_rmm_psa",
        question="What RMM/PSA agents are currently deployed?",
        category=Category.CURRENT_STATE,
        extraction_hint="RMM tool, PSA, ConnectWise, Datto RMM, NinjaRMM, Kaseya, Atera, Autotask, monitoring agents, remote management agents",
    ),
    RFIField(
        row=23, key="other_support_requirements",
        question="Are there any other support requirements we should be aware of?",
        category=Category.CURRENT_STATE,
        extraction_hint="Special support needs, VIP users, executive support, after-hours, weekend support, on-call",
    ),
    RFIField(
        row=24, key="ticket_stats",
        question="Stats for number of support tickets/types per month for the past 6 months? Peak/Off-Peak?",
        category=Category.CURRENT_STATE,
        extraction_hint="Ticket volume, tickets per month, peak periods, busy seasons, common ticket types",
    ),
    RFIField(
        row=25, key="business_hours",
        question="What are the operating hours (Business Hours)?",
        category=Category.CURRENT_STATE,
        extraction_hint="Business hours, operating hours, office hours, 9-5, time zone, shifts",
    ),

    # ── 4. Microsoft 365 & Licensing ────────────────────────────────
    # Row 26 = category header
    RFIField(
        row=27, key="ms_licensing",
        question="What Microsoft licensing is in use? Qty?",
        category=Category.LICENSING,
        extraction_hint="Microsoft 365 plan, Office 365 license type, E3, E5, Business Premium, Business Basic, license count, per-user licensing",
    ),
    RFIField(
        row=28, key="ms_additional_licensing",
        question="Are there any additional Microsoft licensing? Qty?",
        category=Category.LICENSING,
        extraction_hint="MS Phone System, Teams Room, shared mailboxes, Exchange Online Plan, add-on licenses, kiosk licenses",
    ),
    RFIField(
        row=29, key="ms_contract_term",
        question="What is the Microsoft licensing contract term? Annual/Monthly? When does the contract end?",
        category=Category.LICENSING,
        extraction_hint="Microsoft contract term, annual vs monthly, renewal date, contract expiration, EA agreement",
    ),
    RFIField(
        row=30, key="ms_tenants",
        question="How many Microsoft Tenants? Why are there multiple tenants?",
        category=Category.LICENSING,
        extraction_hint="Number of tenants, multiple tenants, tenant migration, tenant consolidation, why separate tenants",
    ),
    RFIField(
        row=31, key="ms_licensing_vendor",
        question="Who do they purchase Microsoft licenses from?",
        category=Category.LICENSING,
        extraction_hint="License vendor, CSP, Pax8, Sherweb, Ingram, direct from Microsoft, licensing partner, who sells them licenses",
    ),
    RFIField(
        row=32, key="google_licensing",
        question="What Google Workspace licensing is in use? Qty?",
        category=Category.LICENSING,
        extraction_hint="Google Workspace plan, Business Starter, Standard, Plus, Enterprise, Gmail, Google Drive",
    ),
    RFIField(
        row=33, key="third_party_licensing",
        question="Is there any other 3rd party licensing provided by the current MSP?",
        category=Category.LICENSING,
        extraction_hint="Adobe, EDR, Mimecast, antivirus, backup software, line of business apps provided by MSP",
    ),

    # ── 5. Servers & Infrastructure ─────────────────────────────────
    # Row 34 = category header
    RFIField(
        row=35, key="server_location",
        question="Where are the servers hosted? Onsite, data center/co-lo, or cloud-based?",
        category=Category.SERVERS,
        extraction_hint="Server location, on-premises, data center, colocation, colo, cloud hosted, hybrid",
    ),
    RFIField(
        row=36, key="server_count",
        question="How many servers are there? How many are physical? How many are virtual?",
        category=Category.SERVERS,
        extraction_hint="Number of servers, physical vs virtual, VM count, server inventory",
    ),
    RFIField(
        row=37, key="server_roles",
        question="What are the server roles?",
        category=Category.SERVERS,
        extraction_hint="Server roles, domain controller, file server, print server, application server, database server, AD, DNS, DHCP",
    ),
    RFIField(
        row=38, key="server_specs",
        question="What are the server specs (CPU, RAM, Disk Space)?",
        category=Category.SERVERS,
        extraction_hint="CPU, RAM, disk space, storage, server hardware model, Dell, HP, Lenovo, server specs",
    ),
    RFIField(
        row=39, key="virtualization",
        question="What virtualization technology is used (e.g., VMware, Hyper-V)?",
        category=Category.SERVERS,
        extraction_hint="VMware, Hyper-V, ESXi, vSphere, virtualization platform, hypervisor",
    ),
    RFIField(
        row=40, key="server_ownership",
        question="Who owns the physical servers? Data center/colo servers? Cloud servers?",
        category=Category.SERVERS,
        extraction_hint="Server ownership, who owns the hardware, leased vs owned, MSP-owned, client-owned",
    ),
    RFIField(
        row=41, key="rented_equipment",
        question="Is there rented/leased hardware that must be returned before go-live?",
        category=Category.SERVERS,
        extraction_hint="Rented equipment, leased hardware, equipment to return, MSP-owned hardware, lease expiration",
    ),
    RFIField(
        row=42, key="offsite_hosted_equipment",
        question="Is there equipment at colocation or hosting facilities?",
        category=Category.SERVERS,
        extraction_hint="Colocation, colo, hosting facility, off-site server, data center rack, remote hosting",
    ),
    RFIField(
        row=43, key="cloud_servers",
        question="Are there Public Cloud Servers (Azure/AWS)?",
        category=Category.SERVERS,
        extraction_hint="Azure, AWS, GCP, cloud VMs, cloud servers, IaaS, public cloud",
    ),
    RFIField(
        row=44, key="cloud_server_roles",
        question="How many cloud servers are there and what are their roles?",
        category=Category.SERVERS,
        extraction_hint="Cloud server count, cloud VM roles, what runs in the cloud",
    ),

    # ── 6. Data, Files & Applications ───────────────────────────────
    # Row 45 = category header
    RFIField(
        row=46, key="file_repository",
        question="File repository location?",
        category=Category.DATA,
        extraction_hint="File storage, file server, SharePoint, OneDrive, Dropbox, Google Drive, NAS, network drive, mapped drives",
    ),
    RFIField(
        row=47, key="total_data_size",
        question="What is total size of data?",
        category=Category.DATA,
        extraction_hint="Data size, total storage, terabytes, gigabytes, how much data",
    ),
    RFIField(
        row=48, key="data_migration",
        question="How much data needs to be migrated?",
        category=Category.DATA,
        extraction_hint="Data migration volume, what needs to move, migration scope",
    ),
    RFIField(
        row=49, key="linked_files",
        question="Are there linked files in spreadsheets?",
        category=Category.DATA,
        extraction_hint="Linked spreadsheets, Excel links, external references, shared workbooks, linked files",
    ),
    RFIField(
        row=50, key="lob_applications",
        question="What line-of-business applications are in use?",
        category=Category.DATA,
        extraction_hint="LOB apps, line of business, industry software, ERP, CRM, accounting, QuickBooks, Great Plains, POS, Toast, Aloha, critical applications, 3rd party apps",
    ),
    RFIField(
        row=51, key="lob_app_vendor_contacts",
        question="Who are the vendor contacts for critical LOB applications?",
        category=Category.DATA,
        extraction_hint="App vendor contact, vendor support number, vendor account rep, application vendor relationship",
    ),
    RFIField(
        row=52, key="saas_inventory",
        question="What SaaS applications are in use beyond M365/Google?",
        category=Category.DATA,
        extraction_hint="SaaS apps, Salesforce, HubSpot, Slack, Zoom, Asana, Monday, cloud applications, software subscriptions",
    ),
    RFIField(
        row=53, key="standard_apps",
        question="Do you have a standard set of applications used across the organization?",
        category=Category.DATA,
        extraction_hint="Standard apps, standard software, SOE, standard operating environment, installed applications, business apps",
    ),

    # ── 7. Email & Communication ────────────────────────────────────
    # Row 54 = category header
    RFIField(
        row=55, key="email_hosting",
        question="Where is email hosted? Office 365/Google/Exchange Server/GoDaddy/etc?",
        category=Category.EMAIL,
        extraction_hint="Email platform, Office 365, Google Workspace, Exchange Online, Exchange Server, GoDaddy, email hosting",
    ),
    RFIField(
        row=56, key="email_migration",
        question="Do emails need to be migrated?",
        category=Category.EMAIL,
        extraction_hint="Email migration, tenant migration, email move, mailbox migration, tenant-to-tenant",
    ),
    RFIField(
        row=57, key="mailbox_count",
        question="How many mailboxes need to be migrated? User & shared?",
        category=Category.EMAIL,
        extraction_hint="Number of mailboxes, user mailboxes, shared mailboxes, mailbox count, email accounts",
    ),
    RFIField(
        row=58, key="public_folders",
        question="Are there Public Folders?",
        category=Category.EMAIL,
        extraction_hint="Public folders, Exchange public folders, shared folders",
    ),
    RFIField(
        row=59, key="email_security",
        question="What Email Security is in place? IE. Proofpoint, Mimecast, Defender for Office 365",
        category=Category.EMAIL,
        extraction_hint="Email security, Proofpoint, Mimecast, Defender for Office 365, email filtering, spam filter, phishing protection",
    ),
    RFIField(
        row=60, key="number_of_domains",
        question="How many domains?",
        category=Category.EMAIL,
        extraction_hint="Number of email domains, domain count, vanity domains, domain names",
    ),
    RFIField(
        row=61, key="domain_website_hosting",
        question="Who manages DNS, domain registration, and website hosting?",
        category=Category.EMAIL,
        extraction_hint="DNS provider, domain registrar, GoDaddy, Cloudflare, website hosting, who manages the domain, DNS management, website host",
    ),
    RFIField(
        row=62, key="collaboration_tools",
        question="What collaboration tools are in use for communication and file sharing?",
        category=Category.EMAIL,
        extraction_hint="Teams, Slack, Zoom, SharePoint, OneDrive, Dropbox, Google Drive, collaboration tools",
    ),
    RFIField(
        row=63, key="phone_system",
        question="What is the current phone system?",
        category=Category.EMAIL,
        extraction_hint="Phone system, PBX, VoIP, Teams Phone, RingCentral, 8x8, Cisco, desk phones, softphone",
    ),
    RFIField(
        row=64, key="phone_upgrade",
        question="Are you looking to change or upgrade the phone system?",
        category=Category.EMAIL,
        extraction_hint="Phone upgrade, new phone system, migrate phone, phone replacement, Teams calling",
    ),
    RFIField(
        row=65, key="voice_recording",
        question="Is there Voice Recording in place and is it required? What system is in place and where is it stored?",
        category=Category.EMAIL,
        extraction_hint="Voice recording, call recording, compliance recording, recording storage, call recorder",
    ),

    # ── 8. Network & Connectivity ───────────────────────────────────
    # Row 66 = category header
    RFIField(
        row=67, key="internet_connectivity",
        question="What internet connectivity is in place (Provider/Speed)?",
        category=Category.NETWORK,
        extraction_hint="ISP, internet provider, bandwidth, speed, fiber, cable, Comcast, AT&T, Mbps, Gbps",
    ),
    RFIField(
        row=68, key="isp_management",
        question="Who manages the ISP relationship at each location?",
        category=Category.NETWORK,
        extraction_hint="ISP management, who manages internet, ISP account, ISP billing, internet vendor relationship",
    ),
    RFIField(
        row=69, key="firewalls",
        question="Number of firewalls and the model(s)?",
        category=Category.NETWORK,
        extraction_hint="Firewall count, firewall model, SonicWall, Fortinet, FortiGate, Meraki, Palo Alto, WatchGuard, Cisco, end of life firewall",
    ),
    RFIField(
        row=70, key="routers",
        question="Number of routers and the model(s)?",
        category=Category.NETWORK,
        extraction_hint="Router count, router model, Cisco, Meraki, Ubiquiti, routing",
    ),
    RFIField(
        row=71, key="switches",
        question="Number of switches and the model(s)?",
        category=Category.NETWORK,
        extraction_hint="Switch count, switch model, Cisco, Meraki, Ubiquiti, HP, managed switch, PoE",
    ),
    RFIField(
        row=72, key="waps",
        question="Number of WAPs and the model(s)?",
        category=Category.NETWORK,
        extraction_hint="Wireless access points, WAP count, WAP model, Meraki, Ubiquiti, Aruba, Wi-Fi, WiFi",
    ),
    RFIField(
        row=73, key="printers_copiers",
        question="What printers/copiers are in the environment? Managed or purchased?",
        category=Category.NETWORK,
        extraction_hint="Printers, copiers, MFP, managed print, print vendor, Ricoh, Canon, HP, Xerox, print service",
    ),
    RFIField(
        row=74, key="network_diagram",
        question="Is there a current Network diagram?",
        category=Category.NETWORK,
        extraction_hint="Network diagram, network map, topology, Visio, network documentation",
    ),
    RFIField(
        row=75, key="other_it_vendors",
        question="Are there existing relationships with other IT vendors or service providers?",
        category=Category.NETWORK,
        extraction_hint="Other IT vendors, ISP, telco, copier vendor, vendor relationships, other providers",
    ),

    # ── 9. Devices & Endpoints ──────────────────────────────────────
    # Row 76 = category header
    RFIField(
        row=77, key="windows_devices",
        question="Number of Windows devices?",
        category=Category.DEVICES,
        extraction_hint="Windows PC count, Windows laptops, Windows desktops, Windows device inventory",
    ),
    RFIField(
        row=78, key="macos_devices",
        question="Number of macOS devices?",
        category=Category.DEVICES,
        extraction_hint="Mac count, MacBooks, iMacs, Apple computers, macOS devices",
    ),
    RFIField(
        row=79, key="mobile_devices",
        question="Number of mobile devices (iPhone/Android)? Corporate or personal?",
        category=Category.DEVICES,
        extraction_hint="iPhone count, Android count, iOS devices, mobile phones, corporate phones, personal phones, BYOD mobile",
    ),
    RFIField(
        row=80, key="device_ownership",
        question="Are devices corporate owned or BYOD?",
        category=Category.DEVICES,
        extraction_hint="Corporate owned, BYOD, bring your own device, company-issued, personal devices",
    ),
    RFIField(
        row=81, key="domain_join",
        question="What are the Devices joined to (Active Directory/Azure AD/Hybrid Azure Joined)?",
        category=Category.DEVICES,
        extraction_hint="Domain joined, Active Directory, Azure AD, Entra ID, hybrid join, workgroup, domain controller",
    ),
    RFIField(
        row=82, key="device_encryption",
        question="Are the devices Encrypted (Bitlocker, File Vault)?",
        category=Category.DEVICES,
        extraction_hint="BitLocker, FileVault, disk encryption, device encryption, full disk encryption",
    ),
    RFIField(
        row=83, key="heavy_workloads",
        question="Do users process heavy workloads on their devices? What processes are run?",
        category=Category.DEVICES,
        extraction_hint="Heavy workloads, rendering, CAD, video editing, data processing, resource-intensive apps",
    ),
    RFIField(
        row=84, key="asset_register",
        question="Is there an Asset Register or Inventory?",
        category=Category.DEVICES,
        extraction_hint="Asset register, inventory list, CMDB, asset tracking, device inventory, hardware list",
    ),

    # ── 10. Security & Compliance ───────────────────────────────────
    # Row 85 = category header
    RFIField(
        row=86, key="cybersecurity_measures",
        question="What cybersecurity measures do you currently have in place?",
        category=Category.SECURITY,
        extraction_hint="Security stack, antivirus, EDR, SIEM, SOC, security tools, firewall, threat detection",
    ),
    RFIField(
        row=87, key="mfa",
        question="What MFA is in place? IE. Azure, Okta, DUO",
        category=Category.SECURITY,
        extraction_hint="Multi-factor authentication, MFA, 2FA, Azure MFA, Okta, DUO, Authenticator app",
    ),
    RFIField(
        row=88, key="sso_provider",
        question="Is there an SSO provider beyond Azure AD (Okta, JumpCloud)?",
        category=Category.SECURITY,
        extraction_hint="SSO, single sign-on, Okta, JumpCloud, OneLogin, Azure AD, identity provider, IdP, SAML",
    ),
    RFIField(
        row=89, key="mdm",
        question="Is there a Mobile Device Management (MDM) solution in place? (Windows & Mac)",
        category=Category.SECURITY,
        extraction_hint="MDM, Intune, Mobile Iron, JAMF, Mosyle, mobile device management, device enrollment, Apple MDM, Mac management",
    ),
    RFIField(
        row=90, key="endpoint_protection",
        question="What endpoint protection is in place?",
        category=Category.SECURITY,
        extraction_hint="Endpoint protection, EDR, antivirus, SentinelOne, CrowdStrike, Defender, Webroot, Sophos, Huntress",
    ),
    RFIField(
        row=91, key="patch_management",
        question="What is the current patch management posture?",
        category=Category.SECURITY,
        extraction_hint="Patch management, Windows updates, WSUS, patching cadence, update policy, third-party patching, patch compliance",
    ),
    RFIField(
        row=92, key="security_awareness_training",
        question="Is security awareness training in place? What platform?",
        category=Category.SECURITY,
        extraction_hint="Security awareness training, KnowBe4, Proofpoint SAT, phishing simulation, security training, cybersecurity training",
    ),
    RFIField(
        row=93, key="cyber_insurance",
        question="Does the company have cyber insurance? Who is the carrier?",
        category=Category.SECURITY,
        extraction_hint="Cyber insurance, cyber liability, insurance carrier, insurance requirements, policy requirements, coverage",
    ),
    RFIField(
        row=94, key="remote_access",
        question="What remote access solutions are in use? IE. VPN, Citrix, Azure Virtual Desktop",
        category=Category.SECURITY,
        extraction_hint="Remote access, VPN, Citrix, AVD, Azure Virtual Desktop, RDP, remote desktop, WVD",
    ),
    RFIField(
        row=95, key="vpn",
        question="Is there a client VPN? Where is the VPN terminating and type of VPN?",
        category=Category.SECURITY,
        extraction_hint="VPN type, site-to-site VPN, client VPN, VPN concentrator, SSL VPN, IPSec, VPN termination point",
    ),
    RFIField(
        row=96, key="remote_support_tool",
        question="What remote support tool is deployed? (ScreenConnect, TeamViewer, Splashtop)",
        category=Category.SECURITY,
        extraction_hint="Remote support tool, ScreenConnect, ConnectWise Control, TeamViewer, Splashtop, remote access to PCs, remote desktop tool",
    ),
    RFIField(
        row=97, key="compliance_requirements",
        question="Are there any compliance requirements or industry-specific regulations?",
        category=Category.SECURITY,
        extraction_hint="Compliance, HIPAA, PCI, SOX, GDPR, CMMC, NIST, industry regulations, audit requirements, PCI-DSS",
    ),
    RFIField(
        row=98, key="archiving",
        question="Which archiving vendor? What is being archived? Number of users?",
        category=Category.SECURITY,
        extraction_hint="Archiving vendor, email archive, Bloomberg archive, Teams archive, compliance archiving, retention policy",
    ),

    # ── 11. Backup & Disaster Recovery ──────────────────────────────
    # Row 99 = category header
    RFIField(
        row=100, key="backup_solution",
        question="What backup solution is in place? What vendor?",
        category=Category.BACKUP,
        extraction_hint="Backup solution, backup vendor, Veeam, Datto, Acronis, BDR, backup appliance, cloud backup, backup frequency",
    ),
    RFIField(
        row=101, key="disaster_recovery_plan",
        question="Is there a disaster recovery plan? What are the RTO/RPO targets?",
        category=Category.BACKUP,
        extraction_hint="Disaster recovery, DR plan, RTO, RPO, recovery time, recovery point, business continuity, failover",
    ),
    RFIField(
        row=102, key="email_backup",
        question="What backup is in place for email/SaaS data?",
        category=Category.BACKUP,
        extraction_hint="Email backup, SaaS backup, backup for 365, Barracuda, Veeam for 365, Spanning, cloud-to-cloud backup",
    ),

    # ── 12. Documentation & Handoff ─────────────────────────────────
    # Row 103 = category header
    RFIField(
        row=104, key="existing_documentation",
        question="Is there existing IT documentation? What platform (IT Glue, Passportal, wiki)?",
        category=Category.DOCUMENTATION,
        extraction_hint="IT documentation, IT Glue, Passportal, Hudu, wiki, documentation platform, knowledge base, runbooks",
    ),
    RFIField(
        row=105, key="admin_credentials",
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
