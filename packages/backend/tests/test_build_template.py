from myhome.build_template import PHASES, seed_default_build


def test_phase_count():
    assert len(PHASES) == 22


def test_task_count():
    total = sum(len(p["tasks"]) for p in PHASES)
    assert total == 58


def test_seed_creates_project_and_phases_and_tasks():
    doc = seed_default_build()
    assert doc.project is not None
    assert doc.project.status == "planning"
    assert len(doc.phases) == 22
    assert len(doc.tasks) == 58
    assert doc.phases[0].nameKey == "build.phases.planning.name"
    assert doc.tasks[0].titleKey == "build.tasks.siteSurvey.title"


def test_seed_chains_tasks_within_phase():
    doc = seed_default_build()
    planning_tasks = [t for t in doc.tasks if t.phaseId == doc.phases[0].id]
    assert len(planning_tasks) == 5
    dep = next(d for d in doc.dependencies if d.successorTaskId == planning_tasks[1].id)
    assert dep.predecessorTaskId == planning_tasks[0].id


def test_seed_links_first_task_of_phase_to_previous_phase_last_task():
    doc = seed_default_build()
    site_prep_phase = doc.phases[1]
    planning_phase = doc.phases[0]
    site_prep_first_task = min(
        (t for t in doc.tasks if t.phaseId == site_prep_phase.id), key=lambda t: t.displayOrder
    )
    planning_last_task = max(
        (t for t in doc.tasks if t.phaseId == planning_phase.id), key=lambda t: t.displayOrder
    )
    dep = next(d for d in doc.dependencies if d.successorTaskId == site_prep_first_task.id)
    assert dep.predecessorTaskId == planning_last_task.id


def test_seed_rough_in_phases_all_depend_on_framing_not_each_other():
    doc = seed_default_build()
    by_slug = {p["slug"]: doc.phases[i] for i, p in enumerate(PHASES)}
    framing_last = max(
        (t for t in doc.tasks if t.phaseId == by_slug["framing"].id), key=lambda t: t.displayOrder
    )
    for slug in ("plumbingRoughIn", "electricalRoughIn", "hvacRoughIn"):
        first_task = min(
            (t for t in doc.tasks if t.phaseId == by_slug[slug].id), key=lambda t: t.displayOrder
        )
        preds = [d.predecessorTaskId for d in doc.dependencies if d.successorTaskId == first_task.id]
        assert preds == [framing_last.id]


def test_seed_insulation_depends_on_all_three_rough_ins():
    doc = seed_default_build()
    by_slug = {p["slug"]: doc.phases[i] for i, p in enumerate(PHASES)}
    insulation_first = min(
        (t for t in doc.tasks if t.phaseId == by_slug["insulation"].id), key=lambda t: t.displayOrder
    )
    preds = {d.predecessorTaskId for d in doc.dependencies if d.successorTaskId == insulation_first.id}
    expected = set()
    for slug in ("plumbingRoughIn", "electricalRoughIn", "hvacRoughIn"):
        last_task = max(
            (t for t in doc.tasks if t.phaseId == by_slug[slug].id), key=lambda t: t.displayOrder
        )
        expected.add(last_task.id)
    assert preds == expected
