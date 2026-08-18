create extension if not exists pgcrypto;

create table if not exists jarvis_tasks (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    lane text not null,
    impact smallint not null check (impact between 1 and 10),
    urgency smallint not null check (urgency between 1 and 10),
    confidence smallint not null check (confidence between 1 and 10),
    effort smallint not null check (effort between 1 and 10),
    status text not null default 'READY' check (status in ('READY','CLAIMED','DONE','FAILED','BLOCKED','WAITING_APPROVAL')),
    claimed_by text,
    lease_until timestamptz,
    capabilities text[] not null default '{}',
    dependencies uuid[] not null default '{}',
    approval_required boolean not null default false,
    approval_granted boolean not null default false,
    idempotency_key text,
    attempts integer not null default 0,
    max_attempts integer not null default 3 check (max_attempts between 1 and 100),
    evidence jsonb not null default '[]'::jsonb,
    limitations text[] not null default '{}',
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (jsonb_typeof(evidence) = 'array'),
    check (jsonb_typeof(payload) = 'object')
);

create unique index if not exists jarvis_tasks_active_idempotency_key
    on jarvis_tasks(idempotency_key)
    where idempotency_key is not null and status <> 'FAILED';
create index if not exists jarvis_tasks_ready_idx
    on jarvis_tasks(status, lease_until, impact desc, urgency desc, confidence desc);

create table if not exists jarvis_audit (
    seq bigint generated always as identity primary key,
    occurred_at timestamptz not null default now(),
    event text not null,
    task_id uuid,
    agent text,
    data jsonb not null default '{}'::jsonb
);

create or replace function jarvis_task_score(t jarvis_tasks) returns numeric
language sql immutable as $$
select round(((0.45*t.impact + 0.30*t.urgency + 0.25*t.confidence) * ((11-t.effort)::numeric/10)),3)
$$;

create or replace function jarvis_deps_done(p_dependencies uuid[]) returns boolean
language sql stable as $$
select not exists (
  select 1 from unnest(coalesce(p_dependencies,'{}')) dep_id
  left join jarvis_tasks dep on dep.id=dep_id
  where dep.id is null or dep.status<>'DONE'
)
$$;

create or replace function jarvis_enqueue(
 p_title text,p_lane text,p_impact smallint,p_urgency smallint,p_confidence smallint,p_effort smallint,
 p_capabilities text[] default '{}',p_dependencies uuid[] default '{}',p_approval_required boolean default false,
 p_idempotency_key text default null,p_max_attempts integer default 3,p_payload jsonb default '{}'::jsonb
) returns uuid language plpgsql as $$
declare v_id uuid;
begin
 if p_idempotency_key is not null then
   select id into v_id from jarvis_tasks where idempotency_key=p_idempotency_key and status<>'FAILED' order by created_at desc limit 1;
   if v_id is not null then return v_id; end if;
 end if;
 insert into jarvis_tasks(title,lane,impact,urgency,confidence,effort,capabilities,dependencies,approval_required,idempotency_key,max_attempts,payload)
 values(p_title,p_lane,p_impact,p_urgency,p_confidence,p_effort,coalesce(p_capabilities,'{}'),coalesce(p_dependencies,'{}'),p_approval_required,p_idempotency_key,p_max_attempts,coalesce(p_payload,'{}'::jsonb)) returning id into v_id;
 insert into jarvis_audit(event,task_id,data) values('TASK_ADDED',v_id,jsonb_build_object('lane',p_lane));
 return v_id;
exception when unique_violation then
 select id into v_id from jarvis_tasks where idempotency_key=p_idempotency_key and status<>'FAILED' limit 1;
 return v_id;
end;
$$;

create or replace function jarvis_claim_next(p_agent text,p_capabilities text[],p_lease_seconds integer default 1800)
returns table(id uuid,title text,lane text,score numeric,capabilities text[],attempts integer,lease_until timestamptz,payload jsonb)
language plpgsql as $$
declare v_id uuid;
begin
 update jarvis_tasks t set status='WAITING_APPROVAL',updated_at=now()
 where t.status='READY' and t.approval_required and not t.approval_granted
   and t.capabilities <@ coalesce(p_capabilities,'{}') and t.attempts<t.max_attempts and jarvis_deps_done(t.dependencies);

 select t.id into v_id from jarvis_tasks t
 where (t.status='READY' or (t.status='CLAIMED' and t.lease_until<now()))
   and (not t.approval_required or t.approval_granted)
   and t.capabilities <@ coalesce(p_capabilities,'{}') and t.attempts<t.max_attempts and jarvis_deps_done(t.dependencies)
 order by jarvis_task_score(t) desc,t.impact desc,t.urgency desc,t.created_at asc
 for update skip locked limit 1;
 if v_id is null then return; end if;
 return query update jarvis_tasks t
 set status='CLAIMED',claimed_by=p_agent,lease_until=now()+make_interval(secs=>greatest(p_lease_seconds,1)),attempts=t.attempts+1,updated_at=now()
 where t.id=v_id returning t.id,t.title,t.lane,jarvis_task_score(t),t.capabilities,t.attempts,t.lease_until,t.payload;
 insert into jarvis_audit(event,task_id,agent,data) values('TASK_CLAIMED',v_id,p_agent,jsonb_build_object('lease_seconds',p_lease_seconds));
end;
$$;

create or replace function jarvis_heartbeat(p_task_id uuid,p_agent text,p_lease_seconds integer default 1800) returns boolean
language plpgsql as $$
declare v_count integer;
begin
 update jarvis_tasks set lease_until=now()+make_interval(secs=>greatest(p_lease_seconds,1)),updated_at=now()
 where id=p_task_id and status='CLAIMED' and claimed_by=p_agent;
 get diagnostics v_count=row_count;
 if v_count=1 then insert into jarvis_audit(event,task_id,agent) values('LEASE_RENEWED',p_task_id,p_agent); return true; end if;
 return false;
end;
$$;

create or replace function jarvis_complete(p_task_id uuid,p_agent text,p_evidence jsonb,p_limitations text[] default '{}') returns boolean
language plpgsql as $$
declare v_count integer;
begin
 if p_evidence is null or jsonb_typeof(p_evidence)<>'array' or jsonb_array_length(p_evidence)=0 then raise exception 'completion requires evidence'; end if;
 if exists(select 1 from jsonb_array_elements(p_evidence) e where coalesce(e->>'type','')='' or coalesce(e->>'ref','')='') then raise exception 'every evidence entry requires type and ref'; end if;
 update jarvis_tasks set status='DONE',evidence=p_evidence,limitations=coalesce(p_limitations,'{}'),lease_until=null,updated_at=now()
 where id=p_task_id and status='CLAIMED' and claimed_by=p_agent;
 get diagnostics v_count=row_count;
 if v_count=1 then insert into jarvis_audit(event,task_id,agent,data) values('TASK_COMPLETED',p_task_id,p_agent,jsonb_build_object('evidence_count',jsonb_array_length(p_evidence))); return true; end if;
 return false;
end;
$$;

create or replace function jarvis_fail(p_task_id uuid,p_agent text,p_reason text,p_retryable boolean default true) returns text
language plpgsql as $$
declare v_status text;
begin
 update jarvis_tasks set status=case when p_retryable and attempts<max_attempts then 'READY' else 'FAILED' end,
 claimed_by=null,lease_until=null,limitations=array[p_reason],updated_at=now()
 where id=p_task_id and status='CLAIMED' and claimed_by=p_agent returning status into v_status;
 if v_status is null then raise exception 'task is not claimed by agent'; end if;
 insert into jarvis_audit(event,task_id,agent,data) values('TASK_FAILED',p_task_id,p_agent,jsonb_build_object('reason',p_reason,'next_status',v_status));
 return v_status;
end;
$$;
