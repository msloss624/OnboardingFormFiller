"""
HubSpot client — search deals, get company info, pull associated contacts,
extract email domain, and fetch engagement notes.
"""
import httpx
from dataclasses import dataclass, field


BASE = "https://api.hubapi.com"


@dataclass
class Contact:
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    job_title: str | None = None

    @property
    def domain(self) -> str | None:
        if self.email and "@" in self.email:
            return self.email.split("@")[1].lower()
        return None


@dataclass
class Company:
    id: str
    name: str
    domain: str | None = None
    city: str | None = None
    state: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    contacts: list[Contact] = field(default_factory=list)

    @property
    def client_domain(self) -> str | None:
        """Best guess at the client's email domain."""
        if self.domain:
            return self.domain.lower()
        for c in self.contacts:
            d = c.domain
            if d:
                return d
        return None


@dataclass
class Deal:
    id: str
    name: str
    stage: str
    amount: str | None = None
    close_date: str | None = None
    company_id: str | None = None


class HubSpotClient:
    def __init__(self, api_key: str):
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.client = httpx.Client(base_url=BASE, headers=self.headers, timeout=30)

    # ── Deals ────────────────────────────────────────────────────────

    def search_deals(self, query: str, limit: int = 10) -> list[Deal]:
        """Search deals by name."""
        resp = self.client.post("/crm/v3/objects/deals/search", json={
            "query": query,
            "limit": limit,
            "properties": ["dealname", "dealstage", "amount", "closedate"],
        })
        resp.raise_for_status()
        deals = []
        for r in resp.json().get("results", []):
            p = r.get("properties", {})
            deals.append(Deal(
                id=r["id"],
                name=p.get("dealname", ""),
                stage=p.get("dealstage", ""),
                amount=p.get("amount"),
                close_date=p.get("closedate"),
            ))
        return deals

    def get_deal_associations(self, deal_id: str, to_object: str = "companies") -> list[str]:
        """Get IDs of objects associated with a deal."""
        resp = self.client.get(f"/crm/v4/objects/deals/{deal_id}/associations/{to_object}")
        resp.raise_for_status()
        return [r["toObjectId"] for r in resp.json().get("results", [])]

    # ── Companies ────────────────────────────────────────────────────

    def get_company(self, company_id: str) -> Company:
        props = "name,domain,city,state,industry,numberofemployees"
        resp = self.client.get(f"/crm/v3/objects/companies/{company_id}", params={"properties": props})
        resp.raise_for_status()
        p = resp.json().get("properties", {})
        emp = p.get("numberofemployees")
        return Company(
            id=company_id,
            name=p.get("name", ""),
            domain=p.get("domain"),
            city=p.get("city"),
            state=p.get("state"),
            industry=p.get("industry"),
            employee_count=int(emp) if emp else None,
        )

    def search_companies(self, query: str, limit: int = 10) -> list[Company]:
        """Search companies by name."""
        resp = self.client.post("/crm/v3/objects/companies/search", json={
            "query": query,
            "limit": limit,
            "properties": ["name", "domain", "city", "state", "industry", "numberofemployees"],
        })
        resp.raise_for_status()
        companies = []
        for r in resp.json().get("results", []):
            p = r.get("properties", {})
            emp = p.get("numberofemployees")
            companies.append(Company(
                id=r["id"],
                name=p.get("name", ""),
                domain=p.get("domain"),
                city=p.get("city"),
                state=p.get("state"),
                industry=p.get("industry"),
                employee_count=int(emp) if emp else None,
            ))
        return companies

    # ── Contacts ─────────────────────────────────────────────────────

    def get_company_contacts(self, company_id: str) -> list[Contact]:
        """Get contacts associated with a company."""
        # Get contact IDs
        resp = self.client.get(f"/crm/v4/objects/companies/{company_id}/associations/contacts")
        resp.raise_for_status()
        contact_ids = [r["toObjectId"] for r in resp.json().get("results", [])]
        if not contact_ids:
            return []

        # Batch-fetch contact details
        contacts = []
        for cid in contact_ids:
            props = "firstname,lastname,email,phone,jobtitle"
            resp = self.client.get(f"/crm/v3/objects/contacts/{cid}", params={"properties": props})
            if resp.status_code == 200:
                p = resp.json().get("properties", {})
                contacts.append(Contact(
                    id=str(cid),
                    first_name=p.get("firstname", ""),
                    last_name=p.get("lastname", ""),
                    email=p.get("email", ""),
                    phone=p.get("phone"),
                    job_title=p.get("jobtitle"),
                ))
        return contacts

    # ── Notes / Engagements ──────────────────────────────────────────

    def get_company_notes(self, company_id: str, limit: int = 50) -> list[dict]:
        """Get notes/engagements associated with a company. Returns raw note bodies."""
        resp = self.client.post("/crm/v3/objects/notes/search", json={
            "filterGroups": [{
                "filters": [{
                    "propertyName": "associations.company",
                    "operator": "EQ",
                    "value": company_id,
                }]
            }],
            "properties": ["hs_note_body", "hs_timestamp", "hs_lastmodifieddate"],
            "limit": limit,
            "sorts": [{"propertyName": "hs_timestamp", "direction": "DESCENDING"}],
        })
        if resp.status_code != 200:
            # Notes API might not be available (requires opt-in)
            return []
        return [
            {
                "body": r.get("properties", {}).get("hs_note_body", ""),
                "timestamp": r.get("properties", {}).get("hs_timestamp", ""),
            }
            for r in resp.json().get("results", [])
            if r.get("properties", {}).get("hs_note_body")
        ]

    # ── High-level: get everything for a deal ────────────────────────

    def get_deal_context(self, deal_id: str) -> dict:
        """Pull all relevant data for a deal: company info, contacts, notes."""
        # Get associated company
        company_ids = self.get_deal_associations(deal_id, "companies")
        if not company_ids:
            return {"error": "No company associated with this deal"}

        company = self.get_company(str(company_ids[0]))
        contacts = self.get_company_contacts(company.id)
        company.contacts = contacts
        notes = self.get_company_notes(company.id)

        return {
            "company": company,
            "contacts": contacts,
            "notes": notes,
            "client_domain": company.client_domain,
        }

    def close(self):
        self.client.close()
