"""
Mock Companies House responses — used when CH_API_KEY is not set.
Returns realistic fixture data so the app can be demoed without an API key.
"""

MOCK_COMPANIES: dict[str, dict] = {
    "00000006": {
        "company_number": "00000006",
        "company_name": "DEMO HOLDINGS LTD",
        "company_status": "active",
        "type": "ltd",
        "date_of_creation": "2010-03-15",
        "registered_office_address": {
            "address_line_1": "1 Demo Street",
            "locality": "London",
            "postal_code": "EC2A 1AA",
            "country": "England",
        },
        "sic_codes": ["64205", "70100"],
        "accounts": {"overdue": False},
        "confirmation_statement": {"overdue": False},
        "has_charges": False,
        "has_insolvency_history": False,
        "jurisdiction": "england-wales",
    },
    "00000007": {
        "company_number": "00000007",
        "company_name": "DEMO SUBSIDIARY LTD",
        "company_status": "active",
        "type": "ltd",
        "date_of_creation": "2015-07-20",
        "registered_office_address": {
            "address_line_1": "2 Demo Road",
            "locality": "Manchester",
            "postal_code": "M1 1AA",
            "country": "England",
        },
        "sic_codes": ["62020"],
        "accounts": {"overdue": True},
        "confirmation_statement": {"overdue": False},
        "has_charges": True,
        "has_insolvency_history": False,
        "jurisdiction": "england-wales",
    },
}

MOCK_OFFICERS: dict[str, list] = {
    "00000006": [
        {
            "name": "SMITH, John James",
            "officer_role": "director",
            "appointed_on": "2010-03-15",
            "nationality": "British",
            "occupation": "Company Director",
            "date_of_birth": {"month": 6, "year": 1975},
            "address": {
                "address_line_1": "1 Service Road",
                "locality": "London",
                "postal_code": "EC1A 1BB",
                "country": "England",
            },
            "links": {"officer": {"appointments": "/officers/abc123/appointments"}},
        },
        {
            "name": "JONES, Sarah",
            "officer_role": "secretary",
            "appointed_on": "2012-01-01",
            "nationality": "British",
            "occupation": "Company Secretary",
            "date_of_birth": {"month": 9, "year": 1980},
            "address": {
                "address_line_1": "2 Service Road",
                "locality": "London",
                "postal_code": "EC1A 1CC",
                "country": "England",
            },
            "links": {"officer": {"appointments": "/officers/def456/appointments"}},
        },
    ],
    "00000007": [
        {
            "name": "SMITH, John James",
            "officer_role": "director",
            "appointed_on": "2015-07-20",
            "nationality": "British",
            "occupation": "Company Director",
            "date_of_birth": {"month": 6, "year": 1975},
            "address": {
                "address_line_1": "1 Service Road",
                "locality": "London",
                "postal_code": "EC1A 1BB",
                "country": "England",
            },
            "links": {"officer": {"appointments": "/officers/abc123/appointments"}},
        },
    ],
}

MOCK_PSCS: dict[str, list] = {
    "00000006": [
        {
            "name": "DEMO PARENT CORP",
            "kind": "corporate-entity-person-with-significant-control",
            "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
            "notified_on": "2016-04-06",
            "identification": {"registration_number": "00000009", "country_registered": "England"},
            "links": {"self": "/company/00000006/persons-with-significant-control/corporate-entity/xxx"},
        },
    ],
    "00000007": [
        {
            "name": "DEMO HOLDINGS LTD",
            "kind": "corporate-entity-person-with-significant-control",
            "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
            "notified_on": "2015-07-20",
            "identification": {"registration_number": "00000006", "country_registered": "England"},
            "links": {"self": "/company/00000007/persons-with-significant-control/corporate-entity/yyy"},
        },
    ],
}

MOCK_FILINGS: dict[str, list] = {
    "00000006": [
        {
            "transaction_id": "MzA5NTQ5MjA5NWFk",
            "description": "Confirmation statement made on 15 March 2024",
            "category": "confirmation-statement",
            "type": "CS01",
            "date": "2024-03-15",
        },
        {
            "transaction_id": "MzA5NTQ5MjA5NWFk2",
            "description": "Total exemption full accounts made up to 31 December 2023",
            "category": "accounts",
            "type": "AA",
            "date": "2024-02-28",
        },
    ],
    "00000007": [
        {
            "transaction_id": "MzA5NTQ5MjA5NWFk3",
            "description": "Confirmation statement made on 20 July 2024",
            "category": "confirmation-statement",
            "type": "CS01",
            "date": "2024-07-20",
        },
    ],
}


class MockCompaniesHouseClient:
    async def search_companies(self, query: str, items_per_page: int = 20, start_index: int = 0) -> dict:
        q = query.lower()
        matches = [
            c for c in MOCK_COMPANIES.values()
            if q in c["company_name"].lower() or q in c["company_number"]
        ]
        return {
            "items": matches[start_index:start_index + items_per_page],
            "total_results": len(matches),
            "items_per_page": items_per_page,
            "start_index": start_index,
        }

    async def get_company(self, number: str) -> dict:
        if number in MOCK_COMPANIES:
            return MOCK_COMPANIES[number]
        # Return a generic unknown company
        return {
            "company_number": number,
            "company_name": f"UNKNOWN COMPANY {number}",
            "company_status": "active",
            "type": "ltd",
            "date_of_creation": None,
            "registered_office_address": {},
            "sic_codes": [],
            "accounts": {"overdue": False},
            "confirmation_statement": {"overdue": False},
            "has_charges": False,
            "has_insolvency_history": False,
            "jurisdiction": "england-wales",
        }

    async def get_officers(self, number: str, items_per_page: int = 100) -> dict:
        items = MOCK_OFFICERS.get(number, [])
        return {"items": items, "total_results": len(items)}

    async def get_pscs(self, number: str) -> dict:
        items = MOCK_PSCS.get(number, [])
        return {"items": items, "total_results": len(items)}

    async def get_filings(self, number: str, items_per_page: int = 25) -> dict:
        items = MOCK_FILINGS.get(number, [])
        return {"items": items, "total_results": len(items)}

    async def close(self) -> None:
        pass
