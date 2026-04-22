"""
Master data: countries, currencies, airports, Charge Master (LogiSight).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, get_current_user, get_db, require_super_admin
from app.models import Airport, Charge, ChargeAlias, Country, Currency
from app.schemas import (
    AirportCreate,
    AirportPatch,
    AirportRead,
    ChargeAliasCreate,
    ChargeAliasRead,
    ChargeCreate,
    ChargeRead,
    ChargeUpdate,
    CountryCreate,
    CountryPatch,
    CountryRead,
    CurrencyCreate,
    CurrencyPatch,
    CurrencyRead,
)

router = APIRouter()


def _forbid_forwarder_charges(role: str | None) -> None:
    if role == "forwarder":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Charge Master is not available")


# --- Countries ---


@router.get("/countries", response_model=list[CountryRead])
async def list_countries(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
    active_only: bool = Query(True),
) -> list[Country]:
    q = select(Country).order_by(Country.name)
    if active_only:
        q = q.where(Country.is_active.is_(True))
    r = await db.execute(q)
    return list(r.scalars().all())


@router.post("/countries", response_model=CountryRead, status_code=status.HTTP_201_CREATED)
async def create_country(
    body: CountryCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Country:
    row = Country(name=body.name, short_name=body.short_name, is_active=True)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/countries/{country_id}", response_model=CountryRead)
async def patch_country(
    country_id: int,
    body: CountryPatch,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Country:
    row = await db.get(Country, country_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    if body.name is not None:
        row.name = body.name
    if body.short_name is not None:
        row.short_name = body.short_name
    if body.is_active is not None:
        row.is_active = body.is_active
    await db.commit()
    await db.refresh(row)
    return row


# --- Currencies ---


@router.get("/currencies", response_model=list[CurrencyRead])
async def list_currencies(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
    active_only: bool = Query(True),
) -> list[Currency]:
    q = select(Currency).order_by(Currency.short_name)
    if active_only:
        q = q.where(Currency.is_active.is_(True))
    r = await db.execute(q)
    return list(r.scalars().all())


@router.post("/currencies", response_model=CurrencyRead, status_code=status.HTTP_201_CREATED)
async def create_currency(
    body: CurrencyCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Currency:
    row = Currency(name=body.name, short_name=body.short_name, is_active=True)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/currencies/{currency_id}", response_model=CurrencyRead)
async def patch_currency(
    currency_id: int,
    body: CurrencyPatch,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Currency:
    row = await db.get(Currency, currency_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    if body.name is not None:
        row.name = body.name
    if body.short_name is not None:
        row.short_name = body.short_name
    if body.is_active is not None:
        row.is_active = body.is_active
    await db.commit()
    await db.refresh(row)
    return row


# --- Airports ---


@router.get("/airports", response_model=list[AirportRead])
async def list_airports(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
    active_only: bool = Query(True),
) -> list[Airport]:
    q = select(Airport).order_by(Airport.iata_code)
    if active_only:
        q = q.where(Airport.is_active.is_(True))
    r = await db.execute(q)
    return list(r.scalars().all())


@router.post("/airports", response_model=AirportRead, status_code=status.HTTP_201_CREATED)
async def create_airport(
    body: AirportCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Airport:
    row = Airport(
        name=body.name,
        iata_code=body.iata_code,
        country_id=body.country_id,
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/airports/{airport_id}", response_model=AirportRead)
async def patch_airport(
    airport_id: int,
    body: AirportPatch,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Airport:
    row = await db.get(Airport, airport_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    if body.name is not None:
        row.name = body.name
    if body.iata_code is not None:
        row.iata_code = body.iata_code
    if body.country_id is not None:
        row.country_id = body.country_id
    if body.is_active is not None:
        row.is_active = body.is_active
    await db.commit()
    await db.refresh(row)
    return row


def _charge_to_read(ch: Charge) -> ChargeRead:
    aliases = [
        ChargeAliasRead(id=int(a.id), charge_id=int(a.charge_id), alias=a.alias) for a in (ch.aliases or [])
    ]
    return ChargeRead(
        id=int(ch.id),
        company_id=int(ch.company_id),
        name=ch.name,
        short_name=ch.short_name,
        is_active=ch.is_active,
        aliases=aliases,
    )


# --- Charge Master ---


@router.get("/charges", response_model=list[ChargeRead])
async def list_charges(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    company_id: int | None = Query(None),
) -> list[ChargeRead]:
    _forbid_forwarder_charges(current_user.get("role"))

    role = current_user.get("role")
    cid: int | None
    if role == "super_admin":
        cid = company_id
        if cid is None:
            raise HTTPException(
                status_code=400,
                detail="super_admin must pass company_id query parameter",
            )
    else:
        cid = current_user.get("company_id")
        if cid is None:
            raise HTTPException(status_code=403, detail="Company scope required")

    r = await db.execute(
        select(Charge)
        .where(Charge.company_id == cid)
        .options(selectinload(Charge.aliases))
        .order_by(Charge.short_name)
    )
    rows = list(r.scalars().unique().all())
    return [_charge_to_read(c) for c in rows]


@router.post("/charges", response_model=ChargeRead, status_code=status.HTTP_201_CREATED)
async def create_charge(
    body: ChargeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChargeRead:
    _forbid_forwarder_charges(current_user.get("role"))
    if current_user.get("role") not in ("client", "super_admin"):
        raise HTTPException(status_code=403, detail="Only client users manage Charge Master")

    cid = current_user.get("company_id")
    if current_user.get("role") == "super_admin":
        raise HTTPException(status_code=400, detail="Use a client JWT to create charges, or extend API with company_id")
    if cid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    ch = Charge(company_id=cid, name=body.name, short_name=body.short_name, is_active=True)
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    r = await db.execute(select(Charge).where(Charge.id == ch.id).options(selectinload(Charge.aliases)))
    ch2 = r.scalar_one()
    return _charge_to_read(ch2)


@router.patch("/charges/{charge_id}", response_model=ChargeRead)
async def patch_charge(
    charge_id: int,
    body: ChargeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChargeRead:
    _forbid_forwarder_charges(current_user.get("role"))
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only client users may update Charge Master")

    uid = current_user.get("company_id")
    if uid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    r0 = await db.execute(
        select(Charge).where(Charge.id == charge_id).options(selectinload(Charge.aliases))
    )
    ch = r0.scalar_one_or_none()
    if ch is None or int(ch.company_id) != int(uid):
        raise HTTPException(status_code=404, detail="Charge not found")

    if body.name is not None:
        ch.name = body.name
    if body.short_name is not None:
        ch.short_name = body.short_name
    if body.is_active is not None:
        ch.is_active = body.is_active
    await db.commit()
    await db.refresh(ch)
    r = await db.execute(select(Charge).where(Charge.id == ch.id).options(selectinload(Charge.aliases)))
    return _charge_to_read(r.scalar_one())


@router.post("/charges/{charge_id}/aliases", response_model=ChargeAliasRead, status_code=status.HTTP_201_CREATED)
async def add_charge_alias(
    charge_id: int,
    body: ChargeAliasCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChargeAlias:
    _forbid_forwarder_charges(current_user.get("role"))
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only client users may add aliases")

    uid = current_user.get("company_id")
    if uid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    ch = await db.get(Charge, charge_id)
    if ch is None or int(ch.company_id) != int(uid):
        raise HTTPException(status_code=404, detail="Charge not found")

    alias = ChargeAlias(charge_id=charge_id, alias=body.alias)
    db.add(alias)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate alias or invalid data") from None
    await db.refresh(alias)
    return ChargeAliasRead(id=int(alias.id), charge_id=int(alias.charge_id), alias=alias.alias)


@router.delete("/charges/{charge_id}/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_charge_alias(
    charge_id: int,
    alias_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    _forbid_forwarder_charges(current_user.get("role"))
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only client users may delete aliases")

    uid = current_user.get("company_id")
    if uid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    ch = await db.get(Charge, charge_id)
    if ch is None or int(ch.company_id) != int(uid):
        raise HTTPException(status_code=404, detail="Charge not found")

    a = await db.get(ChargeAlias, alias_id)
    if a is None or int(a.charge_id) != charge_id:
        raise HTTPException(status_code=404, detail="Alias not found")

    await db.execute(delete(ChargeAlias).where(ChargeAlias.id == alias_id))
    await db.commit()
