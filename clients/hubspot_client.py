"""
HubSpot client — search deals, get company info, pull associated contacts,
extract email domain, and fetch engagement notes.
"""
from __future__ import annotations
import concurrent.futures
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
        self._stage_labels: dict[str, str] | None = None

    def _get_stage_labels(self) -> dict[str, str]:
        """Fetch and cache mapping of stage ID → display label across all pipelines."""
        if self._stage_labels is None:
            resp = self.client.get("/crm/v3/pipelines/deals")
            resp.raise_for_status()
            self._stage_labels = {}
            for pipeline in resp.json().get("results", []):
                for stage in pipeline.get("stages", []):
                    self._stage_labels[stage["id"]] = stage["label"]
        return self._stage_labels

    # ── Deals ────────────────────────────────────────────────────────

    def search_deals(self, query: str, limit: int = 10, pipeline: str = "default") -> list[Deal]:
        """Search deals by name, filtered to a specific pipeline."""
        search_body = {
            "query": query,
            "limit": limit,
            "properties": ["dealname", "dealstage", "amount", "closedate", "pipeline"],
            "filterGroups": [{
                "filters": [
                    {
                        "propertyName": "pipeline",
                        "operator": "EQ",
                        "value": pipeline,
                    },
                    {
                        "propertyName": "dealstage",
                        "operator": "NEQ",
                        "value": "12660608",
                    },
                    {
                        "propertyName": "dealstage",
                        "operator": "NEQ",
                        "value": "8355557",
                    },
                ]
            }]
        }
        resp = self.client.post("/crm/v3/objects/deals/search", json=search_body)
        resp.raise_for_status()
        stage_labels = self._get_stage_labels()
        deals = []
        for r in resp.json().get("results", []):
            p = r.get("properties", {})
            stage_id = p.get("dealstage", "")
            deals.append(Deal(
                id=r["id"],
                name=p.get("dealname", ""),
                stage=stage_labels.get(stage_id, stage_id),
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
            and "Sent by Fireflies.ai" not in r["properties"]["hs_note_body"]
            and "<b>Title</b>:" not in r["properties"]["hs_note_body"]
            and "<strong>Title</strong>:" not in r["properties"]["hs_note_body"]
            and "<h3>" not in r["properties"]["hs_note_body"]
        ]

    # ── Owners ────────────────────────────────────────────────────────

    def get_owner_name(self, owner_id: str) -> str | None:
        """Get the display name of a HubSpot owner by ID."""
        resp = self.client.get(f"/crm/v3/owners/{owner_id}")
        if resp.status_code != 200:
            return None
        data = resp.json()
        first = data.get("firstName", "")
        last = data.get("lastName", "")
        return f"{first} {last}".strip() or None

    # ── Deals (detail) ────────────────────────────────────────────────

    def get_deal_properties(self, deal_id: str) -> dict:
        """Fetch deal properties including owner and close date."""
        props = "dealname,dealstage,amount,closedate,hubspot_owner_id"
        resp = self.client.get(f"/crm/v3/objects/deals/{deal_id}", params={"properties": props})
        resp.raise_for_status()
        return resp.json().get("properties", {})

    # ── High-level: get everything for a deal ────────────────────────

    def get_deal_context(self, deal_id: str) -> dict:
        """Pull all relevant data for a deal: company info, contacts, notes, owner."""
        # Get associated company
        company_ids = self.get_deal_associations(deal_id, "companies")
        if not company_ids:
            return {"error": "No company associated with this deal"}

        company_id = str(company_ids[0])

        # Fetch company, contacts, notes, and deal properties in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            f_company = executor.submit(self.get_company, company_id)
            f_contacts = executor.submit(self.get_company_contacts, company_id)
            f_notes = executor.submit(self.get_company_notes, company_id)
            f_deal_props = executor.submit(self.get_deal_properties, deal_id)

            company = f_company.result()
            contacts = f_contacts.result()
            notes = f_notes.result()
            deal_props = f_deal_props.result()

        company.contacts = contacts

        owner_id = deal_props.get("hubspot_owner_id")
        deal_owner = self.get_owner_name(owner_id) if owner_id else None
        close_date = deal_props.get("closedate")

        return {
            "company": company,
            "contacts": contacts,
            "notes": notes,
            "client_domain": company.client_domain,
            "deal_owner": deal_owner,
            "close_date": close_date,
        }

    def close(self):
        self.client.close()
