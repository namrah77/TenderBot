"""Company Profile — scraped company data + saved checklist as info cards."""
import streamlit as st

from ..components import card, chip_row, empty_state, section_header


def _field(label: str, value) -> None:
    if value in (None, "", [], "not stated"):
        value = "Not stated"
    st.markdown(f'<div class="profile-field-label">{label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="profile-field-value">{value}</div>', unsafe_allow_html=True)


def render_profile(data, checklist: dict, embedded: bool = False) -> None:
    profile = (data or {}).get("company_profile", {}) or {}
    has_scrape = bool(profile)

    if not embedded:
        section_header("Company Profile", "Everything TenderBot knows about you")

    if not data:
        empty_state("Profile not available", "Run an analysis to populate company information.")
        return

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        with card("profile-company"):
            st.markdown('<div class="profile-info-card-title">Company</div>', unsafe_allow_html=True)
            if not has_scrape:
                st.markdown('<span class="muted-note">No company data from the last run.</span>', unsafe_allow_html=True)
            else:
                _field("Company name", profile.get("company_name"))
                _field("Address", profile.get("address"))

        with card("profile-cqc"):
            st.markdown('<div class="profile-info-card-title">CQC</div>', unsafe_allow_html=True)
            if not has_scrape:
                st.markdown('<span class="muted-note">Not available.</span>', unsafe_allow_html=True)
            else:
                _field("CQC ID", profile.get("cqc_id"))
                _field("CQC rating", profile.get("cqc_rating"))

        with card("profile-coverage"):
            st.markdown('<div class="profile-info-card-title">Coverage</div>', unsafe_allow_html=True)
            if not has_scrape:
                st.markdown('<span class="muted-note">Not available.</span>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="profile-field-label">Coverage areas</div>', unsafe_allow_html=True)
                st.markdown(chip_row(profile.get("coverage_areas")), unsafe_allow_html=True)

    with col2:
        with card("profile-services"):
            st.markdown('<div class="profile-info-card-title">Services</div>', unsafe_allow_html=True)
            services = profile.get("services") if has_scrape else checklist.get("services")
            if services:
                st.markdown(chip_row(services), unsafe_allow_html=True)
            else:
                st.markdown('<span class="muted-note">Not yet detected.</span>', unsafe_allow_html=True)

        with card("profile-languages"):
            st.markdown('<div class="profile-info-card-title">Languages</div>', unsafe_allow_html=True)
            langs = profile.get("languages") if has_scrape else checklist.get("languages")
            st.markdown(chip_row(langs), unsafe_allow_html=True)

        with card("profile-certs"):
            st.markdown('<div class="profile-info-card-title">Certifications</div>', unsafe_allow_html=True)
            certs = checklist.get("certifications") or profile.get("certifications")
            st.markdown(chip_row(certs), unsafe_allow_html=True)

        with card("profile-capacity"):
            st.markdown('<div class="profile-info-card-title">Capacity</div>', unsafe_allow_html=True)
            cap = checklist.get("max_capacity_value")
            _field("Max contract capacity", f"£{cap:,}" if cap else None)
            st.markdown('<div class="profile-field-label">Office locations</div>', unsafe_allow_html=True)
            st.markdown(chip_row(checklist.get("office_locations")), unsafe_allow_html=True)

    if not embedded:
        st.caption("Edit checklist details in Settings.")
