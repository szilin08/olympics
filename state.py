import streamlit as st

import db
import logic

BD_KEY = "bd_state_v1"
PK_KEY = "pk_state_v1"
SCHEDULE_KEY = "schedule_v1"


def load_bd():
    bd = db.get_state(BD_KEY)
    if not bd or not bd.get("ties"):
        bd = logic.bd_init()
        db.set_state(BD_KEY, bd, actor="system", action="init")
    return bd


def save_bd(bd, actor="admin", action="update"):
    db.set_state(BD_KEY, bd, actor=actor, action=action)


def load_pk():
    pk = db.get_state(PK_KEY)
    if not pk or not pk.get("groups"):
        pk = logic.pk_init_default()
        db.set_state(PK_KEY, pk, actor="system", action="init")
    return pk


def save_pk(pk, actor="admin", action="update"):
    db.set_state(PK_KEY, pk, actor=actor, action=action)


def load_schedule():
    return db.get_state(SCHEDULE_KEY, {"bd": {}, "pk": {}, "bd_rounds": None, "pk_rounds": None})


def save_schedule(sched, actor="admin"):
    db.set_state(SCHEDULE_KEY, sched, actor=actor, action="schedule_update")


def reset_bd(actor="admin"):
    bd = logic.bd_init()
    save_bd(bd, actor=actor, action="reset_all")
    return bd


def reset_pk(actor="admin"):
    pk = logic.pk_init_default()
    save_pk(pk, actor=actor, action="reset_all")
    return pk
