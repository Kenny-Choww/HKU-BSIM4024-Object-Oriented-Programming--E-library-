import streamlit as st
from datetime import datetime
from manager import LibraryManager
from models import Book, Periodical, Multimedia, Newspaper, Author, Person
from constants import MULTIMEDIA_FORMATS, ITEM_TYPES, USER_ROLES, SUBJECTS, LOCATIONS

# Page Configuration 
st.set_page_config(
    page_title="Library Management System",
    layout="wide",
    page_icon="📚"
)

# Load Custom CSS
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback basic styling if file is missing
        st.markdown("""
            <style>
            .stButton>button { width: 100%; border-radius: 5px; }
            .stExpander { border: 1px solid #f0f2f6; border-radius: 10px; margin-bottom: 10px; }
            </style>
        """, unsafe_allow_html=True)

local_css("styles.css")

# Initialize Session State 
if 'manager' not in st.session_state:
    with st.spinner("Connecting to Database..."):
        st.session_state.manager = LibraryManager()

manager = st.session_state.manager

# --- 3. Helper Validation Functions ---
def is_only_letters(text):
    return all(x.isalpha() or x.isspace() for x in text) if text else False

def is_only_numbers(text):
    return text.isdigit() if text else False

def is_issue_number_unique(issue_no, current_item_id=None):
    if not issue_no:
        return True
    for item in manager.items:
        if isinstance(item, Periodical):
            if current_item_id and str(item.item_id) == str(current_item_id):
                continue
            if str(item.issue_number).strip().lower() == str(issue_no).strip().lower():
                return False
    return True

# --- 4. Sidebar Navigation ---
with st.sidebar:
    st.title("📚 Library Admin")
    st.markdown("---")
    choice = st.radio(
        "Navigation", 
        ["🔍 Search & View", "🆕 Add Item/User", "🔄 Transactions", "📜 Change Records"]
    )
    st.divider()
    if st.button("♻️ Refresh/Reset System"):
        st.session_state.manager.load_data()
        st.success("Data Refreshed!")
        st.rerun()

# --- 5. Core Rendering Function ---
def render_item_list(items, item_type_label, search_query, subject_filter="All"):
    filtered_items = []
    
    for i in items:
        # 1. Search Logic
        id_match = search_query in str(i.item_id).lower()
        title_match = search_query in i.title.lower()
        author_match = False
        if hasattr(i, 'author') and i.author:
            author_match = search_query in i.author.name.lower()
            
        # 2. Subject Filter
        subject_match = True
        if subject_filter != "All":
            if hasattr(i, 'subject'):
                subject_match = (i.subject == subject_filter)
            else:
                subject_match = False

        if (id_match or title_match or author_match) and subject_match:
            filtered_items.append(i)

    if not filtered_items:
        st.info(f"No {item_type_label} match your search criteria.")
        return

    for item in filtered_items:
        edit_mode_key = f"edit_mode_{item.item_id}"
        if edit_mode_key not in st.session_state:
            st.session_state[edit_mode_key] = False

        current_type = type(item).__name__
        is_expanded = st.session_state[edit_mode_key]

        with st.expander(f"{item.item_id} - {item.title} ({current_type})", expanded=is_expanded):
            if not st.session_state[edit_mode_key]:
                # --- VIEW MODE ---
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1.5])
                with col1:
                    st.markdown(f"**ID:** `{item.item_id}`")
                    st.markdown(f"**Title:** {item.title}")
                    st.markdown(f"**Location:** {item.location}")
                with col2:
                    if isinstance(item, Book):
                        st.markdown(f"**Author:** {item.author.name}")
                        st.markdown(f"**Subject:** :blue[{item.subject}]")
                        st.markdown(f"**ISBN:** {item.isbn}")
                    elif isinstance(item, Multimedia):
                        st.markdown(f"**Format:** {item.format_type}")
                    elif isinstance(item, Newspaper):
                        st.markdown(f"**Date:** {item.publish_date}")
                    elif isinstance(item, Periodical):
                        st.markdown(f"**Issue:** {item.issue_number}")
                with col3:
                    st.markdown(f"**Press:** {getattr(item, 'press_org', 'N/A')}")
                    st.markdown(f"**Quantity:** `{getattr(item, 'quantity', 1)}`")
                with col4:
                    # Calculate current borrow count
                    borrow_count = sum(1 for u in manager.users if any(bi.item_id == item.item_id for bi in u.borrowed_items))
                    available_count = max(0, item.quantity - borrow_count)
                    
                    if available_count > 0:
                        st.success(f"✅ Available ({available_count}/{item.quantity})")
                    else:
                        st.error(f"❌ Out of Stock ({borrow_count}/{item.quantity})")
                    
                    if item.due_date:
                        days_late, calc_penalty = manager.calculate_penalty(item.due_date)
                        display_penalty = max(float(item.penalty), calc_penalty)
                        st.warning(f"📅 Last Due: {item.due_date}")
                        if display_penalty > 0:
                            st.markdown(f"⚠️ Penalty: ${display_penalty:.2f}")
                    
                    if st.button("✏️ Edit", key=f"btn_ed_{item.item_id}"):
                        st.session_state[edit_mode_key] = True
                        st.rerun()
            else:
                # --- EDIT MODE ---
                st.markdown("### 🛠️ Edit Item Details")
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_cat = st.selectbox("Category", ITEM_TYPES, index=ITEM_TYPES.index(current_type) if current_type in ITEM_TYPES else 0, key=f"cat_{item.item_id}")
                    new_title = st.text_input("Title", item.title, key=f"t_{item.item_id}")
                    loc_idx = LOCATIONS.index(item.location) if item.location in LOCATIONS else 0
                    new_loc = st.selectbox("Location", LOCATIONS, index=loc_idx, key=f"l_{item.item_id}")
                
                with col2:
                    extra_val = ""
                    author_name = ""
                    new_subject = None
                    if new_cat == "Book":
                        author_name = st.text_input("Author Name", item.author.name if hasattr(item, 'author') else "", key=f"a_{item.item_id}")
                        sub_idx = SUBJECTS.index(item.subject) if (hasattr(item, 'subject') and item.subject in SUBJECTS) else 0
                        new_subject = st.selectbox("Subject", SUBJECTS, index=sub_idx, key=f"sub_{item.item_id}")
                        extra_val = st.text_input("ISBN", item.isbn if hasattr(item, 'isbn') else "", key=f"e_{item.item_id}")
                    elif new_cat == "Multimedia":
                        d_idx = MULTIMEDIA_FORMATS.index(item.format_type) if (isinstance(item, Multimedia) and item.format_type in MULTIMEDIA_FORMATS) else 0
                        extra_val = st.selectbox("Format", MULTIMEDIA_FORMATS, index=d_idx, key=f"e_{item.item_id}")
                    elif new_cat == "Newspaper":
                        extra_val = st.text_input("Publish Date (YYYY-MM-DD)", item.publish_date if hasattr(item, 'publish_date') else "", key=f"e_{item.item_id}")
                    elif new_cat == "Periodical":
                        extra_val = st.text_input("Issue Number", item.issue_number if hasattr(item, 'issue_number') else "", key=f"e_{item.item_id}")
                
                with col3:
                    new_press = st.text_input("Press Organization", getattr(item, 'press_org', "Unknown"), key=f"press_{item.item_id}")
                    new_quantity = st.number_input("Quantity", min_value=1, value=int(getattr(item, 'quantity', 1)), key=f"quant_{item.item_id}")

                st.markdown("---")
                st.subheader("📅 Loan & Penalty Management")
                col_date, col_pen = st.columns(2)
                
                try:
                    current_due_dt = datetime.strptime(item.due_date, "%Y-%m-%d")
                except:
                    current_due_dt = datetime.now()
                
                with col_date:
                    new_due_date_dt = st.date_input("Adjust Due Date", value=current_due_dt, key=f"due_edit_{item.item_id}")
                    new_due_date_str = new_due_date_dt.strftime("%Y-%m-%d")
                
                with col_pen:
                    _, calc_penalty = manager.calculate_penalty(item.due_date)
                    new_penalty = st.number_input(f"Manual Penalty Adjustment ($) - Auto-Calc: ${calc_penalty:.2f}", min_value=0.0, value=float(item.penalty), step=0.5, key=f"pen_edit_{item.item_id}")

                st.markdown("---")
                new_status = st.toggle("Is Available", value=item.is_available, key=f"s_{item.item_id}")
                
                b1, b2, b3 = st.columns(3)
                if b1.button("💾 Save Changes", key=f"save_{item.item_id}", use_container_width=True, type="primary"):
                    if not new_title or not new_loc:
                        st.error("Title and Location cannot be empty.")
                    elif new_cat == "Periodical" and not is_issue_number_unique(extra_val, item.item_id):
                        st.error(f"Issue Number '{extra_val}' is already assigned to another item!")
                    else:
                        manager.update_item_full(
                            item_id=item.item_id, new_cat=new_cat, new_title=new_title, 
                            new_loc=new_loc, new_status=new_status, extra_val=extra_val, 
                            author_name=author_name, subject=new_subject, 
                            new_due_date=new_due_date_str, penalty=new_penalty,
                            press_org=new_press, quantity=new_quantity
                        )
                        st.session_state[edit_mode_key] = False
                        st.success("Updated successfully!")
                        st.rerun()

                if b2.button("🗑️ Delete", key=f"del_{item.item_id}", use_container_width=True):
                    manager.delete_item(item.item_id)
                    st.rerun()
                
                if b3.button("🚫 Cancel", key=f"can_{item.item_id}", use_container_width=True):
                    st.session_state[edit_mode_key] = False
                    st.rerun()

# --- 6. Main Logic ---
if choice == "🔍 Search & View":
    st.title("🔍 Library Explorer")
    
    query = st.text_input(
        "Search Catalog", 
        placeholder="Search by ID, Title, or Author name...",
        help="Type to filter items instantly across all categories."
    ).lower()

    tab_books, tab_per, tab_multi, tab_news, tab_people = st.tabs([
        "📚 Books", "📑 Periodicals", "💿 Multimedia", "📰 Newspapers", "👥 Personnel"
    ])

    with tab_books:
        sub_filter = st.selectbox("Filter by Subject", ["All"] + SUBJECTS)
        render_item_list([i for i in manager.items if isinstance(i, Book)], "Books", query, sub_filter)
    
    with tab_per:
        render_item_list([i for i in manager.items if isinstance(i, Periodical)], "Periodicals", query)
    
    with tab_multi:
        render_item_list([i for i in manager.items if isinstance(i, Multimedia)], "Multimedia", query)
    
    with tab_news:
        render_item_list([i for i in manager.items if isinstance(i, Newspaper)], "Newspapers", query)
    
    with tab_people:
        people_query = [u for u in manager.users if query in u.name.lower() or query in str(u.p_id).lower()]
        if not people_query:
            st.info("No users found matching your search.")
        
        for u in people_query:
            with st.expander(f"👤 {u.p_id} - {u.name} ({u.role})"):
                st.markdown("##### 📚 Active Borrows & Penalty Management")
                borrowed = u.borrowed_items
                
                if borrowed:
                    total_user_penalty = 0
                    for b_item in borrowed:
                        with st.container():
                            days_late, calc_penalty = manager.calculate_penalty(b_item.due_date)
                            current_item_penalty = max(float(b_item.penalty), calc_penalty)
                            total_user_penalty += current_item_penalty
                            
                            col_info, col_date, col_pen_adj, col_btn = st.columns([2, 1.5, 1.5, 1])
                            col_info.markdown(f"**{b_item.title}**\n`{b_item.item_id}`")
                            if days_late > 0:
                                col_info.caption(f"⚠️ Late: {days_late} days")
                            
                            try:
                                curr_due_dt = datetime.strptime(b_item.due_date, "%Y-%m-%d")
                            except:
                                curr_due_dt = datetime.now()
                                
                            new_date = col_date.date_input("Due Date", value=curr_due_dt, key=f"p_date_{u.p_id}_{b_item.item_id}")
                            new_pen_val = col_pen_adj.number_input("Penalty ($)", min_value=0.0, value=float(b_item.penalty), step=0.5, key=f"p_pen_{u.p_id}_{b_item.item_id}")
                            
                            if col_btn.button("Update", key=f"p_upd_{u.p_id}_{b_item.item_id}"):
                                # Determine extra_val based on item type
                                if isinstance(b_item, Book): ev = b_item.isbn
                                elif isinstance(b_item, Periodical): ev = b_item.issue_number
                                elif isinstance(b_item, Newspaper): ev = b_item.publish_date
                                elif isinstance(b_item, Multimedia): ev = b_item.format_type
                                else: ev = ""

                                manager.update_item_full(
                                    item_id=b_item.item_id, 
                                    new_cat=type(b_item).__name__,
                                    new_title=b_item.title, 
                                    new_loc=b_item.location,
                                    new_status=False, 
                                    extra_val=ev,
                                    author_name=b_item.author.name if hasattr(b_item, 'author') else None,
                                    subject=getattr(b_item, 'subject', None),
                                    new_due_date=new_date.strftime("%Y-%m-%d"),
                                    penalty=new_pen_val,
                                    press_org=getattr(b_item, 'press_org', "Unknown"),
                                    quantity=getattr(b_item, 'quantity', 1)
                                )
                                st.success("Record Updated!")
                                st.rerun()
                        st.divider()
                    
                    if total_user_penalty > 0:
                        st.error(f"### 🚩 Total Penalty: ${total_user_penalty:.2f}")
                else:
                    st.info("No active borrows.")

                st.divider()
                st.markdown("##### ⚙️ Manage User Profile")
                c1, c2, c3 = st.columns([2, 2, 1])
                new_pname = c1.text_input("Edit Name", u.name, key=f"un_{u.p_id}")
                new_prole = c2.selectbox("Edit Role", USER_ROLES, index=USER_ROLES.index(u.role), key=f"ur_{u.p_id}")
                
                if c3.button("💾 Save User", key=f"usave_{u.p_id}", use_container_width=True):
                    if not is_only_letters(new_pname):
                        st.error("Name must contain only letters.")
                    else:
                        manager.update_user(u.p_id, new_pname, new_prole)
                        st.success("User updated!")
                        st.rerun()
                if c3.button("🗑️ Remove User", key=f"udel_{u.p_id}", use_container_width=True):
                    manager.delete_user(u.p_id)
                    st.rerun()

elif choice == "🆕 Add Item/User":
    st.title("🆕 Registration")
    tab1, tab2 = st.tabs(["📦 Add New Item", "👤 Add New User"])
        
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            t = st.selectbox("Item Type", ITEM_TYPES)
            iid = st.text_input("Unique ID (e.g., B001)")
            title = st.text_input("Item Title")
            press_org = st.text_input("Press Organization", "Unknown")
        with col2:
            loc = st.selectbox("Shelf Location", LOCATIONS)
            quantity = st.number_input("Item Quantity", min_value=1, value=1)
            auth, sub, extra = "", "", ""
            if t == "Book":
                auth = st.text_input("Author Name")
                sub = st.selectbox("Subject", SUBJECTS)
                extra = st.text_input("ISBN")
            elif t == "Multimedia":
                extra = st.selectbox("Format", MULTIMEDIA_FORMATS)
            elif t == "Newspaper":
                extra = st.date_input("Publish Date")
            elif t == "Periodical":
                extra = st.text_input("Issue Number")

            if st.button("➕ Add Item", type="primary"):
                if not iid or not title:
                    st.error("ID and Title are required!")
                elif any(str(i.item_id).lower() == str(iid).lower() for i in manager.items):
                    st.error(f"Item ID '{iid}' already exists!")
                elif t == "Periodical" and not is_issue_number_unique(extra):
                    st.error(f"Issue Number '{extra}' already exists!")
                else:
                    if t == "Book": newItem = Book(iid, title, loc, Author(auth), extra, sub, press_org=press_org, quantity=quantity)
                    elif t == "Newspaper": newItem = Newspaper(iid, title, loc, str(extra), press_org=press_org, quantity=quantity)
                    elif t == "Periodical": newItem = Periodical(iid, title, loc, extra, press_org=press_org, quantity=quantity)
                    elif t == "Multimedia": newItem = Multimedia(iid, title, loc, extra, press_org=press_org, quantity=quantity)
                    
                    manager.add_item(newItem)
                    st.success(f"Added {t}: {title}")

    with tab2:
        c1, c2 = st.columns(2)
        pid = c1.text_input("User ID (Numbers only)")
        pname = c1.text_input("Full Name (Letters only)")
        prole = c2.selectbox("Role", USER_ROLES)
        if st.button("👤 Register User", type="primary"):
            if not pid or not pname:
                st.error("Please fill in all fields.")
            elif not is_only_numbers(pid):
                st.error("User ID must be numeric.")
            elif any(str(u.p_id) == str(pid) for u in manager.users):
                st.error(f"User ID '{pid}' is already registered.")
            elif not is_only_letters(pname):
                st.error("Name must contain only letters.")
            else:
                manager.add_user(Person(pid, pname, prole))
                st.success(f"User {pname} registered!")

elif choice == "🔄 Transactions":
    st.title("🔄 Borrow & Return")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Borrow Item")
        b_item_id = st.text_input("Enter Item ID to Borrow", key="manual_b_item").strip()
        b_user_id = st.text_input("Enter User ID", key="manual_b_user").strip()
        
        if st.button("Confirm Borrow", use_container_width=True, type="primary"):
            target_item = next((i for i in manager.items if str(i.item_id).lower() == b_item_id.lower()), None)
            target_user = next((u for u in manager.users if str(u.p_id) == b_user_id), None)
            
            if not target_item:
                st.error(f"Item ID `{b_item_id}` not found.")
            elif not target_user:
                st.error(f"User ID `{b_user_id}` not found.")
            else:
                borrow_count = sum(1 for u in manager.users if any(bi.item_id == target_item.item_id for bi in u.borrowed_items))
                if borrow_count >= target_item.quantity:
                    st.error(f"Item `{target_item.title}` is fully borrowed ({borrow_count}/{target_item.quantity}).")
                else:
                    msg = manager.borrow_item(target_item.item_id, target_user.p_id)
                    st.success(msg)
                    st.rerun()

    with col2:
        st.subheader("📥 Return Item")
        r_item_id = st.text_input("Enter Item ID to Return", key="manual_r_item").strip()
        r_user_id = st.text_input("Enter User ID for Verification", key="manual_r_user").strip()
        
        if st.button("Confirm Return", use_container_width=True, type="primary"):
            target_item = next((i for i in manager.items if str(i.item_id).lower() == r_item_id.lower()), None)
            target_user = next((u for u in manager.users if str(u.p_id) == r_user_id), None)
            
            if not target_item:
                st.error(f"Item ID `{r_item_id}` not found.")
            elif not target_user:
                st.error(f"User ID `{r_user_id}` not found.")
            else:
                is_borrower = any(str(bi.item_id).lower() == r_item_id.lower() for bi in target_user.borrowed_items)
                if not is_borrower:
                    st.error(f"User `{target_user.name}` did not borrow item `{target_item.title}`.")
                else:
                    msg = manager.return_item(target_item.item_id, target_user.p_id)
                    st.success(msg)
                    st.rerun()

elif choice == "📜 Change Records":
    st.title("📜 System Logs")
    if not manager.history:
        st.info("No transaction history.")
    else:
        # Show latest first
        for log in reversed(manager.history[-50:]):
            with st.container():
                col_time, col_act, col_det = st.columns([1.2, 1, 3])
                col_time.write(f"🕒 {log.timestamp}")
                col_act.markdown(f"`{log.action}`")
                col_det.write(f"**Item:** {log.item_title} | **User:** {log.person_name}")
                st.divider()
