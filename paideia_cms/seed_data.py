"""
Seed script for Paideia CMS.

Usage:
    bench execute paideia_cms.seed_data.seed_all

Creates all CMS web pages, testimonials, and site configuration
with production content for the Paideia education platform.
"""

import json
import frappe


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _section(section_type, order, background, **kwargs):
    """Return a child-table dict for a Paideia Page Section row."""
    row = {
        "doctype": "Paideia Page Section",
        "section_type": section_type,
        "order": order,
        "background": background,
    }
    for key in ("heading", "subheading", "body", "cta_label", "cta_url"):
        if key in kwargs:
            row[key] = kwargs[key]
    if "items" in kwargs:
        row["items_json"] = json.dumps(kwargs["items"], ensure_ascii=False)
    if "items_json" in kwargs:
        row["items_json"] = (
            kwargs["items_json"]
            if isinstance(kwargs["items_json"], str)
            else json.dumps(kwargs["items_json"], ensure_ascii=False)
        )
    return row


def _insert_page(page_dict):
    """Insert a Paideia Web Page if one with the same slug does not exist."""
    slug = page_dict.get("slug")
    if frappe.db.exists("Paideia Web Page", {"slug": slug}):
        frappe.logger().info(f"Page with slug '{slug}' already exists — skipping.")
        return
    doc = frappe.get_doc(page_dict)
    doc.insert(ignore_permissions=True)
    frappe.logger().info(f"Created page: {doc.title} ({slug})")


def _insert_testimonial(data):
    """Insert a Paideia Testimonial if one with the same person_name does not exist."""
    if frappe.db.exists("Paideia Testimonial", {"person_name": data["person_name"]}):
        frappe.logger().info(
            f"Testimonial for '{data['person_name']}' already exists — skipping."
        )
        return
    doc = frappe.get_doc(data)
    doc.insert(ignore_permissions=True)
    frappe.logger().info(f"Created testimonial: {data['person_name']}")


# ---------------------------------------------------------------------------
# Reusable content blocks
# ---------------------------------------------------------------------------

TRUST_STRIP_ITEMS = [
    {"value": "30+", "title": "Years Experience"},
    {"value": "50+", "title": "University Partners"},
    {"value": "10,000+", "title": "Students Placed"},
    {"value": "200+", "title": "Consultant Partners"},
]

STUDENT_JOURNEY_STEPS = [
    {"step": 1, "title": "Choose Your Course", "description": "Browse programmes and find the right fit for your goals."},
    {"step": 2, "title": "Check Requirements", "description": "Review entry requirements and English language tests."},
    {"step": 3, "title": "Apply", "description": "Submit your application with our guidance and support."},
    {"step": 4, "title": "Get Your Offer", "description": "Receive and accept your university offer."},
    {"step": 5, "title": "Apply for Visa", "description": "We help you prepare your visa application."},
    {"step": 6, "title": "Arrive & Settle", "description": "Pre-departure briefing, accommodation, and welcome support."},
]


# ---------------------------------------------------------------------------
# Page definitions
# ---------------------------------------------------------------------------

def _pages():
    """Return the list of all page dicts to seed."""
    return [
        # ------------------------------------------------------------------
        # Homepage
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Homepage",
            "slug": "index",
            "audience": "All",
            "status": "Published",
            "hero_headline": "Shaping the future of higher education, together.",
            "hero_subheadline": (
                "Paideia connects universities, students, and consultants across the globe "
                "\u2014 delivering recruitment, compliance, and campus solutions with 30+ years of expertise."
            ),
            "hero_cta_label": "Explore Our Services",
            "hero_cta_url": "/universities",
            "sections": [
                _section("Trust Strip", 1, "White", items=TRUST_STRIP_ITEMS),
                _section("Audience Cards", 2, "White", items=[
                    {"icon": "\U0001f3db\ufe0f", "title": "For Universities", "description": "Student recruitment, UKVI compliance, London campus setup, and more.", "link": "/universities"},
                    {"icon": "\U0001f393", "title": "For Students", "description": "Find your ideal university, apply for scholarships, and get visa support.", "link": "/students"},
                    {"icon": "\U0001f91d", "title": "For Consultants", "description": "Access our university portfolio, earn competitive commissions, and grow your business.", "link": "/consultants"},
                ]),
                _section("CTA Banner", 3, "Dark",
                    heading="Ready to transform your education journey?",
                    subheading="Whether you\u2019re a university, student, or consultant \u2014 Paideia is your partner.",
                    cta_label="Get in Touch",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # Universities landing
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Universities",
            "slug": "universities",
            "audience": "Universities",
            "status": "Published",
            "hero_headline": "Your global student recruitment partner",
            "hero_subheadline": "Paideia helps UK and international universities attract, recruit, and retain the best students from around the world.",
            "hero_cta_label": "Partner With Us",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="What Makes Us Different",
                    items=[
                        {"icon": "\U0001f30d", "title": "Global Reach", "description": "Access to a network of 200+ education consultants in 30+ countries."},
                        {"icon": "\u2705", "title": "UKVI Compliance", "description": "End-to-end CAS management and compliance advisory to protect your licence."},
                        {"icon": "\U0001f3d7\ufe0f", "title": "Campus Development", "description": "From feasibility to fit-out \u2014 we help you establish a London campus."},
                        {"icon": "\U0001f4ca", "title": "Data-Driven", "description": "Market intelligence and student analytics to optimise your recruitment strategy."},
                    ],
                ),
                _section("Service Models", 2, "Grey",
                    heading="Partnership Models",
                    items=[
                        {"title": "Recruitment Partner", "description": "We act as your extended recruitment team, sourcing and converting students across our global network.", "best_for": "Universities seeking volume growth"},
                        {"title": "Compliance Advisory", "description": "UKVI licence support, CAS management, and audit preparation.", "best_for": "Institutions needing regulatory support"},
                        {"title": "London Campus Setup", "description": "Site selection, fit-out, staffing, and student pipeline for your London teaching centre.", "best_for": "International universities entering the UK market"},
                        {"title": "Full-Service Partnership", "description": "Combines recruitment, compliance, and campus operations into one integrated solution.", "best_for": "Universities wanting a complete UK strategy"},
                    ],
                    cta_label="Explore Partnerships",
                    cta_url="/contact",
                ),
                _section("Testimonials", 3, "White"),
                _section("CTA Banner", 4, "Dark",
                    heading="Let\u2019s build your recruitment strategy",
                    cta_label="Contact Us",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # universities/recruitment
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Student Recruitment Services",
            "slug": "universities/recruitment",
            "audience": "Universities",
            "status": "Published",
            "hero_headline": "Student Recruitment Services",
            "hero_subheadline": "Paideia connects your university with qualified, motivated students from around the world through our network of 200+ trusted education consultants.",
            "hero_cta_label": "Start Recruiting",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="Our Recruitment Approach",
                    items=[
                        {"icon": "\U0001f50d", "title": "Market Analysis", "description": "We identify the best source markets for your programmes and profile."},
                        {"icon": "\U0001f91d", "title": "Consultant Network", "description": "Direct access to our vetted network of education agents in 30+ countries."},
                        {"icon": "\U0001f4cb", "title": "Application Management", "description": "End-to-end support from enquiry to enrolment."},
                        {"icon": "\U0001f4c8", "title": "Performance Tracking", "description": "Transparent reporting on pipeline, conversions, and ROI."},
                    ],
                ),
                _section("Process Steps", 2, "Grey",
                    heading="How It Works",
                    items=[
                        {"step": 1, "title": "Discovery", "description": "We learn about your university, programmes, and recruitment goals."},
                        {"step": 2, "title": "Strategy", "description": "We design a tailored recruitment plan targeting the right markets."},
                        {"step": 3, "title": "Activation", "description": "Our consultant network begins promoting your programmes."},
                        {"step": 4, "title": "Management", "description": "We manage applications, interviews, and offer processes."},
                        {"step": 5, "title": "Enrolment", "description": "We support students through to visa and arrival."},
                        {"step": 6, "title": "Review", "description": "Regular performance reviews to optimise results."},
                    ],
                ),
                _section("CTA Banner", 3, "Dark",
                    heading="Ready to grow your international student numbers?",
                    cta_label="Get Started",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # universities/ukvi-compliance
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "UKVI Compliance & CAS Management",
            "slug": "universities/ukvi-compliance",
            "audience": "Universities",
            "status": "Published",
            "hero_headline": "UKVI Compliance & CAS Management",
            "hero_subheadline": "Protect your sponsor licence with expert compliance advisory, CAS management, and audit preparation.",
            "hero_cta_label": "Talk to Our Team",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="Compliance Services",
                    items=[
                        {"icon": "\U0001f6e1\ufe0f", "title": "Licence Protection", "description": "Proactive monitoring and reporting to maintain your UKVI sponsor licence."},
                        {"icon": "\U0001f4c4", "title": "CAS Management", "description": "End-to-end CAS issuance, tracking, and compliance checks."},
                        {"icon": "\U0001f50d", "title": "Audit Preparation", "description": "Mock audits, documentation reviews, and staff training for UKVI visits."},
                        {"icon": "\U0001f4da", "title": "Policy Development", "description": "Create robust attendance, progression, and reporting frameworks."},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Ensure your compliance is watertight",
                    cta_label="Book a Consultation",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # universities/london-campus
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "London Campus Setup",
            "slug": "universities/london-campus",
            "audience": "Universities",
            "status": "Published",
            "hero_headline": "London Campus Setup",
            "hero_subheadline": "Establish your London teaching centre with end-to-end support \u2014 from site selection to student pipeline.",
            "hero_cta_label": "Explore Options",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Process Steps", 1, "White",
                    heading="Campus Development Process",
                    items=[
                        {"step": 1, "title": "Feasibility Study", "description": "Market analysis, regulatory review, and financial modelling."},
                        {"step": 2, "title": "Site Selection", "description": "Identify and secure the ideal London location for your campus."},
                        {"step": 3, "title": "Design & Fit-Out", "description": "Classroom design, IT infrastructure, and campus branding."},
                        {"step": 4, "title": "Licensing & Compliance", "description": "UKVI registration, OfS compliance, and quality assurance."},
                        {"step": 5, "title": "Staffing", "description": "Recruit academic and administrative staff."},
                        {"step": 6, "title": "Student Recruitment", "description": "Activate our recruitment channels to fill your programmes."},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Ready to open your London campus?",
                    cta_label="Let\u2019s Talk",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # universities/slc-recruitment
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "SLC Student Recruitment",
            "slug": "universities/slc-recruitment",
            "audience": "Universities",
            "status": "Published",
            "hero_headline": "SLC Student Recruitment",
            "hero_subheadline": "Recruit UK-domiciled students eligible for Student Loans Company funding through targeted domestic marketing.",
            "hero_cta_label": "Learn More",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="SLC Recruitment Services",
                    items=[
                        {"icon": "\U0001f4b7", "title": "SLC-Eligible Recruitment", "description": "Targeted campaigns to attract students eligible for UK government-backed student loans."},
                        {"icon": "\U0001f4e3", "title": "Domestic Marketing", "description": "Digital and community-based outreach across the UK."},
                        {"icon": "\U0001f3af", "title": "Conversion Optimisation", "description": "From enquiry to enrolment \u2014 we maximise your conversion rates."},
                        {"icon": "\U0001f4ca", "title": "Reporting", "description": "Transparent pipeline and performance reporting."},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Boost your domestic student numbers",
                    cta_label="Contact Us",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # universities/campus-development
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Campus Development Services",
            "slug": "universities/campus-development",
            "audience": "Universities",
            "status": "Published",
            "hero_headline": "Campus Development Services",
            "hero_subheadline": "From new builds to refurbishments \u2014 we help universities create inspiring learning environments.",
            "hero_cta_label": "Start a Project",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="What We Offer",
                    items=[
                        {"icon": "\U0001f3d7\ufe0f", "title": "New Campus Builds", "description": "End-to-end project management for new campus facilities."},
                        {"icon": "\U0001f527", "title": "Refurbishment", "description": "Modernise existing spaces to meet current teaching and technology standards."},
                        {"icon": "\U0001f4bb", "title": "IT Infrastructure", "description": "Network, AV, and digital learning environment setup."},
                        {"icon": "\U0001f3a8", "title": "Campus Branding", "description": "Signage, wayfinding, and branded environments."},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Transform your campus",
                    cta_label="Get in Touch",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # Students landing
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Students",
            "slug": "students",
            "audience": "Students",
            "status": "Published",
            "hero_headline": "Find your place at a world-class university",
            "hero_subheadline": "Paideia guides you through every step \u2014 from choosing the right course to arriving on campus.",
            "hero_cta_label": "Start Your Journey",
            "hero_cta_url": "/students/apply",
            "sections": [
                _section("Audience Cards", 1, "White", items=[
                    {"icon": "\U0001f4dd", "title": "How to Apply", "description": "Step-by-step guide to applying to UK universities.", "link": "/students/apply"},
                    {"icon": "\U0001f393", "title": "Scholarships", "description": "Explore scholarships and funding options.", "link": "/students/scholarships"},
                    {"icon": "\U0001f6c2", "title": "Visa Guide", "description": "Everything you need to know about UK student visas.", "link": "/students/visa"},
                    {"icon": "\U0001f3db\ufe0f", "title": "Partner Universities", "description": "Browse our portfolio of 50+ university partners.", "link": "/students/universities"},
                ]),
                _section("Process Steps", 2, "Grey",
                    heading="Your Journey to the UK",
                    items=STUDENT_JOURNEY_STEPS,
                ),
                _section("Testimonials", 3, "White"),
                _section("CTA Banner", 4, "Dark",
                    heading="Ready to start your UK education journey?",
                    cta_label="Apply Now",
                    cta_url="/students/apply",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # students/apply
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "How to Apply",
            "slug": "students/apply",
            "audience": "Students",
            "status": "Published",
            "hero_headline": "How to Apply",
            "hero_subheadline": "Follow our simple step-by-step guide to apply to a UK university through Paideia.",
            "hero_cta_label": "Contact an Advisor",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Process Steps", 1, "White",
                    heading="Application Steps",
                    items=STUDENT_JOURNEY_STEPS,
                ),
                _section("Rich Text", 2, "Grey",
                    heading="What You\u2019ll Need",
                    body=(
                        "<ul>"
                        "<li><strong>Academic transcripts</strong> \u2014 certified copies of your qualifications</li>"
                        "<li><strong>English language certificate</strong> \u2014 IELTS, TOEFL, or equivalent</li>"
                        "<li><strong>Personal statement</strong> \u2014 why you want to study this course</li>"
                        "<li><strong>Passport copy</strong> \u2014 valid for your intended period of study</li>"
                        "<li><strong>References</strong> \u2014 academic or professional references</li>"
                        "</ul>"
                    ),
                ),
                _section("CTA Banner", 3, "Dark",
                    heading="Need help with your application?",
                    cta_label="Speak to an Advisor",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # students/scholarships
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Scholarships & Funding",
            "slug": "students/scholarships",
            "audience": "Students",
            "status": "Published",
            "hero_headline": "Scholarships & Funding",
            "hero_subheadline": "Explore scholarships, bursaries, and funding options available through our university partners.",
            "hero_cta_label": "Check Eligibility",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Scholarship List", 1, "White",
                    heading="Available Scholarships",
                    items=[
                        {"title": "Paideia Excellence Award", "amount": "\u00a35,000", "description": "Merit-based scholarship for high-achieving international students.", "eligibility": "First-class or equivalent GPA"},
                        {"title": "Global Diversity Scholarship", "amount": "\u00a33,000", "description": "Supporting students from underrepresented regions.", "eligibility": "Students from Sub-Saharan Africa, Central Asia, or South America"},
                        {"title": "Early Bird Discount", "amount": "\u00a32,000", "description": "Tuition fee reduction for early applicants.", "eligibility": "Applications submitted before March 31"},
                        {"title": "Postgraduate Research Fund", "amount": "\u00a310,000", "description": "Funding for outstanding postgraduate research proposals.", "eligibility": "Masters or PhD applicants with strong research proposals"},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Find the right funding for your studies",
                    cta_label="Talk to Us",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # students/visa
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "UK Student Visa Guide",
            "slug": "students/visa",
            "audience": "Students",
            "status": "Published",
            "hero_headline": "UK Student Visa Guide",
            "hero_subheadline": "Everything you need to know about applying for a UK Student visa (formerly Tier 4).",
            "hero_cta_label": "Get Visa Support",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Process Steps", 1, "White",
                    heading="Visa Application Steps",
                    items=[
                        {"step": 1, "title": "Accept Your Offer", "description": "Accept your unconditional offer and receive your CAS number."},
                        {"step": 2, "title": "Gather Documents", "description": "Passport, CAS, financial evidence, English language proof."},
                        {"step": 3, "title": "Complete Online Application", "description": "Apply online via the UK government visa portal."},
                        {"step": 4, "title": "Biometrics Appointment", "description": "Book and attend your biometrics appointment at a visa centre."},
                        {"step": 5, "title": "Wait for Decision", "description": "Standard processing is 3 weeks; priority options available."},
                        {"step": 6, "title": "Travel to the UK", "description": "Collect your BRP within 10 days of arrival."},
                    ],
                ),
                _section("FAQ", 2, "Grey",
                    heading="Frequently Asked Questions",
                    items=[
                        {"title": "How much does a UK student visa cost?", "description": "The standard Student visa costs \u00a3490. You\u2019ll also need to pay the Immigration Health Surcharge (IHS) of \u00a3776 per year."},
                        {"title": "How much money do I need in my bank account?", "description": "You need to show \u00a31,334 per month (up to 9 months) for living costs if studying in London, or \u00a31,023 per month outside London, plus your first year\u2019s tuition fees."},
                        {"title": "Can I work on a student visa?", "description": "Yes \u2014 you can work up to 20 hours per week during term time and full-time during holidays if studying at degree level or above."},
                        {"title": "How long does visa processing take?", "description": "Standard processing takes about 3 weeks. Priority (5 working days) and super-priority (next working day) services are available in some countries."},
                    ],
                ),
                _section("CTA Banner", 3, "Dark",
                    heading="Need help with your visa application?",
                    cta_label="Contact Us",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # students/universities
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Our Partner Universities",
            "slug": "students/universities",
            "audience": "Students",
            "status": "Published",
            "hero_headline": "Our Partner Universities",
            "hero_subheadline": "Browse our portfolio of 50+ accredited UK and international university partners.",
            "hero_cta_label": "Explore Universities",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Rich Text", 1, "White",
                    heading="Why Study With a Paideia Partner?",
                    body=(
                        "<p>All of our partner universities are fully accredited and regulated by the UK\u2019s Office for Students (OfS) or equivalent international bodies. "
                        "When you study with a Paideia partner, you benefit from:</p>"
                        "<ul>"
                        "<li><strong>Quality-assured programmes</strong> \u2014 validated and recognised globally</li>"
                        "<li><strong>Dedicated student support</strong> \u2014 pastoral care, academic guidance, and career services</li>"
                        "<li><strong>Scholarship opportunities</strong> \u2014 exclusive funding options through Paideia</li>"
                        "<li><strong>Post-study work options</strong> \u2014 Graduate Route visa eligibility at most partners</li>"
                        "</ul>"
                    ),
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Find the right university for you",
                    cta_label="Speak to an Advisor",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # Consultants landing
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Consultants",
            "slug": "consultants",
            "audience": "Consultants",
            "status": "Published",
            "hero_headline": "Grow your consultancy with Paideia",
            "hero_subheadline": "Join our global network of education consultants and access premium university partnerships, competitive commissions, and dedicated support.",
            "hero_cta_label": "Register Now",
            "hero_cta_url": "/consultants/register",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="Why Partner With Paideia?",
                    items=[
                        {"icon": "\U0001f3db\ufe0f", "title": "Premium University Portfolio", "description": "50+ accredited UK and international universities."},
                        {"icon": "\U0001f4b0", "title": "Competitive Commissions", "description": "Industry-leading commission rates paid on time, every time."},
                        {"icon": "\U0001f4e6", "title": "Marketing Resources", "description": "Ready-made brochures, presentations, and digital assets."},
                        {"icon": "\U0001f9d1\u200d\U0001f4bc", "title": "Dedicated Support", "description": "A named account manager to support your growth."},
                    ],
                ),
                _section("Service Models", 2, "Grey",
                    heading="Partnership Tiers",
                    items=[
                        {"title": "Standard Partner", "description": "Access to our university portfolio and standard commission rates.", "best_for": "New consultants starting their agency"},
                        {"title": "Premium Partner", "description": "Enhanced commissions, priority application processing, and co-branded materials.", "best_for": "Established consultants with 50+ students per year"},
                        {"title": "Strategic Partner", "description": "Custom commission structures, exclusive university access, and joint marketing campaigns.", "best_for": "Large agencies with 200+ students per year"},
                    ],
                    cta_label="Apply for Partnership",
                    cta_url="/consultants/register",
                ),
                _section("Process Steps", 3, "White",
                    heading="How to Get Started",
                    items=[
                        {"step": 1, "title": "Register", "description": "Complete our online registration form."},
                        {"step": 2, "title": "Verification", "description": "We verify your agency credentials and experience."},
                        {"step": 3, "title": "Onboarding", "description": "Meet your account manager and access our partner portal."},
                        {"step": 4, "title": "Start Recruiting", "description": "Begin submitting applications and earning commissions."},
                    ],
                ),
                _section("CTA Banner", 4, "Dark",
                    heading="Ready to join our network?",
                    cta_label="Register Today",
                    cta_url="/consultants/register",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # consultants/portfolio
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "University Portfolio",
            "slug": "consultants/portfolio",
            "audience": "Consultants",
            "status": "Published",
            "hero_headline": "University Portfolio",
            "hero_subheadline": "Access our curated portfolio of 50+ accredited universities across the UK and internationally.",
            "hero_cta_label": "Download Portfolio",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Rich Text", 1, "White",
                    heading="Our University Partners",
                    body=(
                        "<p>Our portfolio includes Russell Group universities, post-92 institutions, and specialist colleges "
                        "covering a wide range of programmes from foundation to PhD level.</p>"
                        "<p>Key subject areas include:</p>"
                        "<ul>"
                        "<li>Business &amp; Management</li>"
                        "<li>Computing &amp; IT</li>"
                        "<li>Engineering</li>"
                        "<li>Health &amp; Social Care</li>"
                        "<li>Law</li>"
                        "<li>Arts &amp; Design</li>"
                        "</ul>"
                        "<p>Contact your account manager for the full, up-to-date portfolio with commission rates.</p>"
                    ),
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Want access to the full portfolio?",
                    cta_label="Contact Us",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # consultants/commission
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Commission Structure",
            "slug": "consultants/commission",
            "audience": "Consultants",
            "status": "Published",
            "hero_headline": "Commission Structure",
            "hero_subheadline": "Transparent, competitive commission rates \u2014 paid on time, every time.",
            "hero_cta_label": "View Rates",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="Commission Highlights",
                    items=[
                        {"icon": "\U0001f4b7", "title": "Competitive Rates", "description": "Industry-leading commission percentages across all partner universities."},
                        {"icon": "\u23f1\ufe0f", "title": "Timely Payments", "description": "Commissions paid within 30 days of student enrolment confirmation."},
                        {"icon": "\U0001f4c8", "title": "Volume Bonuses", "description": "Higher rates as your student numbers grow."},
                        {"icon": "\U0001f50d", "title": "Full Transparency", "description": "Real-time tracking of your applications and commission status."},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Ready to earn with Paideia?",
                    cta_label="Register Now",
                    cta_url="/consultants/register",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # consultants/resources
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Marketing Resources",
            "slug": "consultants/resources",
            "audience": "Consultants",
            "status": "Published",
            "hero_headline": "Marketing Resources",
            "hero_subheadline": "Everything you need to promote our university partners to your students.",
            "hero_cta_label": "Access Resources",
            "hero_cta_url": "/contact",
            "sections": [
                _section("Feature Cards", 1, "White",
                    heading="Available Resources",
                    items=[
                        {"icon": "\U0001f4c4", "title": "University Brochures", "description": "Downloadable brochures for each partner university."},
                        {"icon": "\U0001f5a5\ufe0f", "title": "Presentation Decks", "description": "Ready-made presentations for student events and webinars."},
                        {"icon": "\U0001f5bc\ufe0f", "title": "Digital Assets", "description": "Social media graphics, banners, and email templates."},
                        {"icon": "\U0001f4ca", "title": "Market Reports", "description": "Country-specific market intelligence and student trend data."},
                    ],
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Need custom marketing materials?",
                    cta_label="Talk to Your Account Manager",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # consultants/register
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Register as a Paideia Partner",
            "slug": "consultants/register",
            "audience": "Consultants",
            "status": "Published",
            "hero_headline": "Register as a Paideia Partner",
            "hero_subheadline": "Join our global network of education consultants. Registration takes just 5 minutes.",
            "hero_cta_label": "Start Registration",
            "hero_cta_url": "#register-form",
            "sections": [
                _section("Process Steps", 1, "White",
                    heading="Registration Process",
                    items=[
                        {"step": 1, "title": "Complete the Form", "description": "Fill in your agency details and experience."},
                        {"step": 2, "title": "Submit Documents", "description": "Upload your business registration and relevant credentials."},
                        {"step": 3, "title": "Review", "description": "Our team reviews your application within 48 hours."},
                        {"step": 4, "title": "Welcome Aboard", "description": "Once approved, access the partner portal and start recruiting."},
                    ],
                ),
                _section("Rich Text", 2, "Grey",
                    heading="What We Look For",
                    body=(
                        "<ul>"
                        "<li>A registered education consultancy or agency</li>"
                        "<li>Experience in international student recruitment</li>"
                        "<li>Commitment to ethical recruitment practices</li>"
                        "<li>Ability to provide accurate guidance to students</li>"
                        "</ul>"
                    ),
                ),
                _section("CTA Banner", 3, "Dark",
                    heading="Ready to join?",
                    cta_label="Register Now",
                    cta_url="#register-form",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # About
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "About Paideia",
            "slug": "about",
            "audience": "All",
            "status": "Published",
            "hero_headline": "About Paideia",
            "hero_subheadline": "A global education consultancy connecting universities, students, and consultants for over 30 years.",
            "sections": [
                _section("Rich Text", 1, "White",
                    heading="Our Story",
                    body=(
                        "<p>Founded in Dubai, Paideia has spent over three decades building bridges between universities and students across the globe. "
                        "What started as a small consultancy has grown into a comprehensive education services provider, working with 50+ universities "
                        "and a network of 200+ education consultants worldwide.</p>"
                        "<p>Our mission is simple: to make quality higher education accessible to every student, regardless of where they come from. "
                        "We do this by partnering with leading universities to provide recruitment, compliance, and campus solutions \u2014 while supporting "
                        "students and consultants every step of the way.</p>"
                    ),
                ),
                _section("Rich Text", 2, "Grey",
                    heading="Our Mission",
                    body=(
                        "<p>To be the most trusted partner in global higher education \u2014 delivering value to universities through ethical recruitment, "
                        "empowering students with life-changing opportunities, and enabling consultants to grow their businesses with confidence.</p>"
                    ),
                ),
                _section("Trust Strip", 3, "White", items=TRUST_STRIP_ITEMS),
                _section("CTA Banner", 4, "Dark",
                    heading="Want to work with us?",
                    cta_label="Get in Touch",
                    cta_url="/contact",
                ),
            ],
        },

        # ------------------------------------------------------------------
        # Contact
        # ------------------------------------------------------------------
        {
            "doctype": "Paideia Web Page",
            "title": "Contact Us",
            "slug": "contact",
            "audience": "All",
            "status": "Published",
            "hero_headline": "Contact Us",
            "hero_subheadline": "Get in touch with our team. We\u2019d love to hear from you.",
            "sections": [
                _section("Rich Text", 1, "White",
                    heading="Get in Touch",
                    body=(
                        "<p>Whether you\u2019re a university looking for a recruitment partner, a student planning your education journey, "
                        "or a consultant wanting to join our network \u2014 we\u2019re here to help.</p>"
                        "<p><strong>Email:</strong> info@paideia.ae<br>"
                        "<strong>Phone:</strong> +971 4 xxx xxxx<br>"
                        "<strong>Address:</strong> Dubai, United Arab Emirates</p>"
                        "<p>Our team typically responds within 24 hours during business days.</p>"
                    ),
                ),
                _section("CTA Banner", 2, "Dark",
                    heading="Prefer to schedule a call?",
                    cta_label="Book a Meeting",
                    cta_url="#book-meeting",
                ),
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Testimonial definitions
# ---------------------------------------------------------------------------

def _testimonials():
    """Return the list of all testimonial dicts to seed."""
    return [
        {
            "doctype": "Paideia Testimonial",
            "quote": "Paideia transformed our international recruitment strategy. We saw a 40% increase in applications within the first year.",
            "person_name": "Dr. Sarah Mitchell",
            "role": "Pro Vice-Chancellor International",
            "organisation": "University of Westminster",
            "audience": "Universities",
            "status": "Published",
        },
        {
            "doctype": "Paideia Testimonial",
            "quote": "The compliance advisory service is outstanding. They helped us prepare for our UKVI audit with confidence.",
            "person_name": "James Chen",
            "role": "Head of Compliance",
            "organisation": "London Metropolitan University",
            "audience": "Universities",
            "status": "Published",
        },
        {
            "doctype": "Paideia Testimonial",
            "quote": "Paideia made my university application so easy. From choosing my course to getting my visa \u2014 they were with me every step.",
            "person_name": "Amara Okafor",
            "role": "MSc Business Analytics Student",
            "organisation": "University of Greenwich",
            "audience": "Students",
            "status": "Published",
        },
        {
            "doctype": "Paideia Testimonial",
            "quote": "The scholarship support was incredible. I received a \u00a35,000 award that made my dream of studying in London possible.",
            "person_name": "Ravi Sharma",
            "role": "BSc Computer Science Student",
            "organisation": "University of East London",
            "audience": "Students",
            "status": "Published",
        },
        {
            "doctype": "Paideia Testimonial",
            "quote": "Since partnering with Paideia, our agency revenue has grown by 60%. The commission structure and support are unmatched.",
            "person_name": "Fatima Al-Rashid",
            "role": "Managing Director",
            "organisation": "Global Education Partners",
            "audience": "Consultants",
            "status": "Published",
        },
        {
            "doctype": "Paideia Testimonial",
            "quote": "The marketing resources and dedicated account manager make it easy to promote universities to our students.",
            "person_name": "Carlos Rodriguez",
            "role": "Senior Consultant",
            "organisation": "EduPath International",
            "audience": "Consultants",
            "status": "Published",
        },
    ]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def seed_pages():
    """Create all Paideia Web Page documents."""
    pages = _pages()
    for page_dict in pages:
        _insert_page(page_dict)
    frappe.db.commit()
    print(f"seed_pages: processed {len(pages)} pages.")


def seed_testimonials():
    """Create all Paideia Testimonial documents."""
    testimonials = _testimonials()
    for t in testimonials:
        _insert_testimonial(t)
    frappe.db.commit()
    print(f"seed_testimonials: processed {len(testimonials)} testimonials.")


def seed_site_config():
    """Populate the Paideia Site Config (Single doctype)."""
    config = frappe.get_single("Paideia Site Config")
    config.site_name = "Paideia"
    config.contact_email = "info@paideia.ae"
    config.contact_phone = "+971 4 xxx xxxx"
    config.address = "Dubai, United Arab Emirates"
    config.linkedin_url = "https://linkedin.com/company/paideia"
    config.save(ignore_permissions=True)
    frappe.db.commit()
    print("seed_site_config: site configuration saved.")


def seed_all():
    """
    Master seed function — creates all CMS content.

    Usage:
        bench execute paideia_cms.seed_data.seed_all
    """
    print("=" * 60)
    print("Paideia CMS — Seeding data")
    print("=" * 60)

    print("\n--- Seeding pages ---")
    seed_pages()

    print("\n--- Seeding testimonials ---")
    seed_testimonials()

    print("\n--- Seeding site config ---")
    seed_site_config()

    print("\n" + "=" * 60)
    print("Seed complete.")
    print("=" * 60)
