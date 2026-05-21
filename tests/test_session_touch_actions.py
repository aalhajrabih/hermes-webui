from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SESSIONS_JS = (ROOT / "static" / "sessions.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def _block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"{start_marker!r} not found"
    end = source.find(end_marker, start)
    assert end != -1, f"{end_marker!r} not found after {start_marker!r}"
    return source[start:end]


def _sessions_block(start_marker: str, end_marker: str) -> str:
    return _block(SESSIONS_JS, start_marker, end_marker)


def test_session_menu_uses_viewport_height_not_fixed_scroll_cap():
    assert "max-height:calc(100vh - 16px)" in STYLE_CSS
    session_menu = STYLE_CSS[STYLE_CSS.find(".session-action-menu{"):STYLE_CSS.find(".session-action-menu.open")]
    assert "max-height:320px" not in session_menu


def test_session_menu_has_subtle_open_animation():
    session_menu = STYLE_CSS[STYLE_CSS.find(".session-action-menu{"):STYLE_CSS.find(".session-action-menu.open")]
    assert "will-change:opacity,transform" in session_menu
    assert "transform-origin:top right" in session_menu
    assert "function _playSessionActionMenuEntrance(menu){" in SESSIONS_JS
    assert "typeof menu.animate==='function'" in SESSIONS_JS
    assert "{opacity:0, transform:'translate3d(0,-4px,0) scale(.985)'}" in SESSIONS_JS
    assert "{duration:450, easing:'cubic-bezier(.2,.8,.2,1)'}" in SESSIONS_JS
    assert "menu.classList.add('open-animated')" in SESSIONS_JS
    assert ".session-action-menu.open-animated{animation:session-menu-in .45s cubic-bezier(.2,.8,.2,1);}" in STYLE_CSS
    assert "@keyframes session-menu-in" in STYLE_CSS
    assert "@media (prefers-reduced-motion:reduce)" in STYLE_CSS
    assert ".session-action-menu{animation:none;will-change:auto;}" in STYLE_CSS
    assert ".session-item,.session-item.dragging,.session-item.session-reflowing,.session-item.swipe-committed,.session-item.swipe-removing{transition:none;}" in STYLE_CSS
    assert ".session-item.long-pressing,.session-item.session-swipe-returning{animation:none;}" in STYLE_CSS


def test_mobile_session_menu_opens_from_long_press_and_hides_dots():
    assert "_longPressDelay=400" in SESSIONS_JS
    assert "el.classList.add('long-pressing')" in SESSIONS_JS
    assert "if(!_longPressMenuOpened) el.classList.remove('long-pressing')" in SESSIONS_JS
    assert "row.classList.remove('menu-open','long-pressing')" in SESSIONS_JS
    assert "_openSessionActionMenu(s, el)" in SESSIONS_JS
    assert "@media (hover:none) and (pointer:coarse)" in STYLE_CSS
    assert ".session-actions{display:none;}" in STYLE_CSS
    assert "const _beginSessionGesture=(clientX,clientY,pointerType='')=>{" in SESSIONS_JS
    assert "const _scheduleSessionLongPressMenu=()=>{" in SESSIONS_JS
    mobile_touch = STYLE_CSS[STYLE_CSS.find("@media (hover:none) and (pointer:coarse)"):STYLE_CSS.find("@media (max-width: 340px)")]
    assert ".session-item{padding-right:6px;}" in mobile_touch
    assert ".session-item.streaming,.session-item.unread{padding-right:40px;}" in mobile_touch
    assert ".session-item:focus-within,.session-item.menu-open{padding-right:6px;}" in mobile_touch


def test_open_session_menu_consumes_next_row_activation():
    assert "if(_sessionActionMenu&&!_sessionActionMenu.contains(target)){" in SESSIONS_JS
    assert "closeSessionActionMenu();" in SESSIONS_JS
    assert "e.stopPropagation();" in SESSIONS_JS
    assert "const stopMenuPointer=(e)=>e.stopPropagation();" in SESSIONS_JS
    assert "menuBtn.onpointerdown=stopMenuPointer;" in SESSIONS_JS
    assert "menuBtn.onpointerup=stopMenuPointer;" in SESSIONS_JS
    menu_btn_idx = SESSIONS_JS.find("menuBtn.onpointerdown=stopMenuPointer;")
    menu_click_idx = SESSIONS_JS.find("menuBtn.onclick=(e)=>{", menu_btn_idx)
    assert menu_btn_idx > 0 and menu_click_idx > menu_btn_idx
    assert "const _isSessionActionTarget=(target)=>{" in SESSIONS_JS
    assert "return !!(actions&&target&&actions.contains(target));" in SESSIONS_JS
    assert "if(_isSessionActionTarget(e.target)) return;" in SESSIONS_JS
    assert "if(_isSessionActionTarget(target)){_gestureState='idle';return false;}" in SESSIONS_JS
    assert "if(_longPressMenuOpened){_gestureState='idle';return true;}" in SESSIONS_JS
    finish_idx = SESSIONS_JS.find("const _finishSessionGesture=(clientX,clientY,target,pointerType)=>{")
    dismiss_idx = SESSIONS_JS.find("if(_sessionActionMenu&&!_sessionActionMenu.contains(target)){", finish_idx)
    load_idx = SESSIONS_JS.find("await loadSession(s.session_id)", finish_idx)
    pointerup_idx = SESSIONS_JS.find("el.onpointerup=(e)=>{")
    assert finish_idx > 0 and load_idx > finish_idx
    assert dismiss_idx > finish_idx and dismiss_idx < load_idx
    assert "if(_finishSessionGesture(e.clientX,e.clientY,e.target,e.pointerType)) e.stopPropagation();" in SESSIONS_JS[pointerup_idx:]


def test_session_swipes_route_archive_restore_and_delete():
    assert "_gesturePointerType!=='mouse'" in SESSIONS_JS
    assert "_swipeTracking=true" in SESSIONS_JS
    assert "_archiveSwipeActionThreshold=128" in SESSIONS_JS
    assert "_deleteSwipeActionThreshold=128" in SESSIONS_JS
    assert "const SESSION_SWIPE_DURATION_MS = 500;" in SESSIONS_JS
    assert "const SESSION_SWIPE_REFLOW_LEAD_MS = 220;" in SESSIONS_JS
    assert "const committedSwipeDuration=_sessionPrefersReducedMotion()?0:SESSION_SWIPE_DURATION_MS;" in SESSIONS_JS
    assert "const committedSwipeReflowDelay=Math.max(0,committedSwipeDuration-SESSION_SWIPE_REFLOW_LEAD_MS);" in SESSIONS_JS
    swipe_block = _sessions_block("const _handleSessionSwipe=(signedDx,signedDy)=>{", "const _commitSessionSwipe=()=>{")
    assert "const actionThreshold=signedDx>0?_archiveSwipeActionThreshold:_deleteSwipeActionThreshold;" in SESSIONS_JS
    assert "if(Math.abs(signedDx)<actionThreshold) return false;" in SESSIONS_JS
    assert "const _updateSessionGesture=(clientX,clientY)=>{" in SESSIONS_JS
    assert "if(_isSessionSwipeTarget()&&(_swipeTracking||dx>dy)) _paintSessionSwipe(signedDx)" in SESSIONS_JS
    assert "if(_updateSessionGesture(touch.clientX,touch.clientY)) e.preventDefault();" in SESSIONS_JS
    assert "_beginSessionGesture(touch.clientX,touch.clientY,'touch');" in SESSIONS_JS
    restore_start = swipe_block.find("if(s.archived){")
    archive_start = swipe_block.find("}else{", restore_start)
    delete_start = swipe_block.find("}else if(_canSwipeDeleteSession()){", archive_start)
    restore_branch = swipe_block[restore_start:archive_start]
    archive_branch = swipe_block[archive_start:delete_start]
    delete_branch = swipe_block[delete_start:]
    assert "_settleSessionSwipePaint();" in restore_branch
    assert "_completeSessionSwipePaint(signedDx);" not in restore_branch
    assert "_archiveSession(s,false,()=>_waitForSessionMotion(committedSwipeDuration))" in restore_branch
    archived_visible_start = swipe_block.find("}else if(_showArchived){")
    assert archived_visible_start > restore_start
    archived_visible_branch = swipe_block[archived_visible_start:archive_start]
    assert "_settleSessionSwipePaint();" in archived_visible_branch
    assert "_completeSessionSwipePaint(signedDx);" not in archived_visible_branch
    assert "_archiveSession(s,true,()=>_waitForSessionMotion(committedSwipeDuration))" in archived_visible_branch
    assert archive_branch.find("_completeSessionSwipePaint(signedDx);") < archive_branch.find("_archiveSession(s,true,()=>_waitForSessionMotion(committedSwipeReflowDelay))")
    assert delete_branch.find("deleteSession(s.session_id,async()=>{") < delete_branch.find("_completeSessionSwipePaint(signedDx);")
    assert "showToast('Imported sessions cannot be deleted here.',3000);" in SESSIONS_JS
    assert "let _gestureState='idle';" in SESSIONS_JS
    assert "const _commitSessionSwipe=()=>{" in SESSIONS_JS
    assert "if(_gestureState==='committed'){" in SESSIONS_JS
    assert SESSIONS_JS.count("if(e.pointerType==='touch') return;") >= 3
    assert "if(_gesturePointerType==='mouse'&&_gestureState!=='idle') _clearPointerDragState();" in SESSIONS_JS


def test_session_swipe_paint_uses_transform_only_exit():
    paint = _sessions_block("const _paintSessionSwipe=(signedDx)=>{", "const _clearSessionSwipePaint=()=>{")
    clear = _sessions_block("const _clearSessionSwipePaint=()=>{", "const _settleSessionSwipePaint=()=>{")
    complete = _sessions_block("const _completeSessionSwipePaint=(signedDx)=>{", "const _handleSessionSwipe=(signedDx,signedDy)=>{")
    assert "--session-swipe-offset" in paint
    assert "--session-swipe-reveal" in paint
    assert "--session-swipe-progress" in paint
    assert "const reveal=Math.abs(offset);" in paint
    assert "window.innerWidth+'px'" in complete
    assert "el.style.height=rect.height+'px'" in complete
    assert "requestAnimationFrame(()=>el.classList.add('swipe-removing'))" in complete
    assert "requestAnimationFrame(()=>requestAnimationFrame(_clearSessionSwipePaint))" in SESSIONS_JS
    assert "el.classList.remove('swiping-right','swiping-left','swipe-committed','swipe-removing')" in clear
    assert ".session-item.swipe-committed,\n  .session-item.swipe-removing{transition:" in STYLE_CSS
    assert "transition:background .15s,color .15s,transform .5s cubic-bezier(.22,.61,.36,1),box-shadow .15s ease" in STYLE_CSS
    assert "transform:translate3d(calc(-1 * var(--session-swipe-offset,0px)),0,0)" in STYLE_CSS
    assert "transform:scale(var(--session-swipe-icon-scale,1))" in STYLE_CSS
    assert "min-width:36px" not in STYLE_CSS[STYLE_CSS.find(".session-swipe-affordance{"):STYLE_CSS.find(".session-swipe-affordance-right{")]
    swipe_start = STYLE_CSS.find(".session-item.swipe-removing{")
    swipe_end = STYLE_CSS.find("}", swipe_start)
    assert swipe_start >= 0 and swipe_end > swipe_start
    swipe_removing = STYLE_CSS[swipe_start:swipe_end]
    assert "height:0" not in swipe_removing
    assert "padding-top:0" not in swipe_removing
    assert "margin-bottom:0" not in swipe_removing
    assert "transform:translate3d(var(--session-swipe-offset,0),var(--session-reflow-offset,0),0)" in STYLE_CSS


def test_session_removal_reflows_surviving_rows_smoothly():
    assert "let _pendingSessionReflowPositions = null;" in SESSIONS_JS
    assert "const _optimisticallyRemovedSessionIds = new Set();" in SESSIONS_JS
    assert "const _sessionSwipeReturnOffsets = new Map();" in SESSIONS_JS
    capture = _sessions_block("function _captureSessionReflowPositions(){", "function _waitForSessionMotion")
    helper = _sessions_block("function _playSessionRowsReflowFromPositions", "function _sessionPrefersReducedMotion")
    assert "positions.set(row.dataset.sid,row.getBoundingClientRect().top);" in capture
    assert "const delta=oldTop-row.getBoundingClientRect().top;" in helper
    assert "const movingRows=[];" in helper
    assert "list.getBoundingClientRect();" in helper
    assert helper.count("getBoundingClientRect()") == 2
    assert "row.style.transition='none';" in helper
    assert "row.classList.add('session-reflowing')" in helper
    assert "requestAnimationFrame(()=>requestAnimationFrame(()=>{" in helper
    assert SESSIONS_JS.count("_pendingSessionReflowPositions=reflowPositions;") >= 2
    assert "const reflowBefore=animateRefresh?flipBefore:_pendingSessionReflowPositions;" in SESSIONS_JS
    assert "const reflowTimeout=animateRefresh?SESSION_LIST_FLIP_TIMEOUT_MS:SESSION_REFLOW_TIMEOUT_MS;" in SESSIONS_JS
    assert "_playSessionRowsReflowFromPositions(reflowBefore,reflowTimeout,_sessionPrefersReducedMotion);" in SESSIONS_JS
    assert "async function _archiveSession(session, archived=true, beforeListRender=null){" in SESSIONS_JS
    assert "const renderHold=beforeListRender?Promise.resolve().then(beforeListRender):null;" in SESSIONS_JS
    assert "if(renderHold) await renderHold;" in SESSIONS_JS
    assert "const serverSessions=_optimisticallyRemovedSessionIds.size" in SESSIONS_JS
    assert "? (sessData.sessions||[]).filter(s=>s&&!_optimisticallyRemovedSessionIds.has(s.session_id))" in SESSIONS_JS
    assert ".session-item.session-reflowing{transition:background .15s,color .15s,transform .36s cubic-bezier(.2,.8,.2,1),box-shadow .15s ease;will-change:transform;}" in STYLE_CSS
    assert "if(_showArchived&&!_sessionPrefersReducedMotion()) _sessionSwipeReturnOffsets.set(session.session_id,'0px');" in SESSIONS_JS
    assert "const swipeReturnOffset=_sessionSwipeReturnOffsets.get(s.session_id);" in SESSIONS_JS
    assert "el.classList.add('session-swipe-returning');" in SESSIONS_JS
    assert "@keyframes sessionSwipeReturn" in STYLE_CSS
    assert ".session-item.session-swipe-returning{animation:sessionSwipeReturn .5s cubic-bezier(.22,.61,.36,1) both;will-change:transform,opacity;}" in STYLE_CSS
    delete_start = SESSIONS_JS.find("async function deleteSession(sid, beforeDelete=null){")
    delete_end = SESSIONS_JS.find("// ── Project helpers", delete_start)
    assert delete_start >= 0 and delete_end > delete_start
    delete_body = SESSIONS_JS[delete_start:delete_end]
    hold_start = delete_body.find("const beforeDeleteHold=beforeDelete?Promise.resolve().then(beforeDelete):null;")
    delete_request = delete_body.find("const deleteRequest=api('/api/session/delete'")
    hold_await = delete_body.find("await beforeDeleteHold;", hold_start)
    optimistic_set = delete_body.find("_optimisticallyRemovedSessionIds.add(sid);")
    optimistic_filter = delete_body.find("_allSessions=(_allSessions||[]).filter")
    optimistic_render = delete_body.find("renderSessionListFromCache();", optimistic_filter)
    response_await = delete_body.find("const deleteResult=await deleteRequest;")
    rollback = delete_body.find("_optimisticallyRemovedSessionIds.delete(sid);")
    final_render = delete_body.find("void renderSessionList().finally(()=>_optimisticallyRemovedSessionIds.delete(sid));")
    assert delete_body.find("const reflowPositions=_captureSessionReflowPositions();") < hold_start < delete_request < hold_await < optimistic_set < optimistic_filter < optimistic_render < response_await < rollback < final_render
    assert "}, error=>({error}));" in delete_body


def test_ios_touch_events_drive_session_swipes():
    assert "el.addEventListener('touchstart'" in SESSIONS_JS
    assert "el.addEventListener('touchmove'" in SESSIONS_JS
    assert "el.addEventListener('touchcancel',_clearPointerDragState" in SESSIONS_JS
    assert "el.addEventListener('touchend'" in SESSIONS_JS
    assert "const _finishSessionGesture=(clientX,clientY,target,pointerType)=>{" in SESSIONS_JS
    assert "{passive:false}" in SESSIONS_JS
    assert "if(_updateSessionGesture(touch.clientX,touch.clientY)) e.preventDefault();" in SESSIONS_JS
    assert SESSIONS_JS.count("if(e.pointerType==='touch') return;") >= 3
    assert "if(_finishSessionGesture(touch.clientX,touch.clientY,e.target,'touch')) e.stopPropagation();" in SESSIONS_JS
    assert "window.PointerEvent" not in SESSIONS_JS


def test_touch_session_rows_preserve_vertical_scroll():
    assert ".session-item{padding:8px 8px;" in STYLE_CSS
    item_rule = STYLE_CSS[STYLE_CSS.find(".session-item{padding:8px 8px;"):STYLE_CSS.find("}", STYLE_CSS.find(".session-item{padding:8px 8px;"))]
    assert "touch-action:pan-y" in item_rule
    assert "user-select:none" in item_rule
    assert "-webkit-user-select:none" in item_rule
    assert "-webkit-touch-callout:none" in item_rule
