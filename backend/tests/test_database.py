"""
test_database.py — database layer (DKC 57 extensions included).
"""

import asyncio
import os


def test_init_db_creates_schema_and_is_idempotent():
    import database

    async def run():
        await database.init_db()
        await database.init_db()  # idempotent — migrations must not raise
        conn = await database._get_connection()
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in await cursor.fetchall()}
        await conn.close()
        assert {"projects", "clips", "settings"} <= tables

        # DKC 57 columns exist
        cursor = await database._get_connection()
        cur = await cursor.execute("PRAGMA table_info(projects)")
        cols = {r[1] for r in await cur.fetchall()}
        await cursor.close()
        assert {"config", "error_message", "source_file", "source_type"} <= cols

    asyncio.run(run())


def test_create_project_with_config_and_source():
    import database

    async def run():
        result = await database.create_project(
            youtube_url="",
            config={"num_clips": 3, "reframe": True},
            source_type="upload",
            source_file="/tmp/x.mp4",
        )
        pid = result["project_id"]
        assert result["status"] == "pending"

        project = await database.get_project(pid)
        assert project["source_type"] == "upload"
        assert project["source_file"] == "/tmp/x.mp4"
        assert project["config"]["num_clips"] == 3

        await database.delete_project(pid)
        assert await database.get_project(pid) is None

    asyncio.run(run())


def test_error_message_persistence():
    import database

    async def run():
        pid = (await database.create_project("https://youtu.be/abc"))["project_id"]
        await database.update_project_status(pid, "error")
        await database.update_project_error(pid, "FFmpeg not found")

        project = await database.get_project(pid)
        assert project["status"] == "error"
        assert project["error_message"] == "FFmpeg not found"

        # clear on retry
        await database.update_project_error(pid, None)
        project = await database.get_project(pid)
        assert project["error_message"] is None
        await database.delete_project(pid)

    asyncio.run(run())


def test_clip_rename_and_delete():
    import database

    async def run():
        pid = (await database.create_project("https://youtu.be/abc"))["project_id"]
        clip = await database.save_clip(
            project_id=pid, file_path="/files/x/clips/clip.mp4",
            start_time=0.0, end_time=30.0, title="orig", viral_score=8,
        )
        assert clip["duration"] == 30.0

        await database.update_clip_title(clip["id"], "renamed")
        got = await database.get_clip(clip["id"])
        assert got["title"] == "renamed"

        ok = await database.delete_clip(clip["id"])
        assert ok
        assert await database.get_clip(clip["id"]) is None
        await database.delete_project(pid)

    asyncio.run(run())


def test_stats_counts():
    import database

    async def run():
        stats0 = await database.get_stats()
        pid1 = (await database.create_project("https://youtu.be/abc"))["project_id"]
        pid2 = (await database.create_project("https://youtu.be/def"))["project_id"]
        await database.update_project_status(pid2, "error")
        await database.save_clip(pid1, "/files/a.mp4", 0, 45, title="s1")
        await database.save_clip(pid1, "/files/b.mp4", 45, 90, title="s2")

        stats = await database.get_stats()
        assert stats["videos"] == stats0["videos"] + 2
        assert stats["shorts"] == stats0["shorts"] + 2
        # delta-based: other tests may leave pending projects behind
        assert stats["processing"] - stats0["processing"] == 1  # pid1 pending
        assert stats["failed"] - stats0["failed"] == 1          # pid2 error

        await database.delete_project(pid1)
        await database.delete_project(pid2)

    asyncio.run(run())


def test_get_all_clips_joins_project_title():
    import database

    async def run():
        pid = (await database.create_project("https://youtu.be/abc"))["project_id"]
        await database.update_project_title(pid, "My Podcast")
        await database.save_clip(pid, "/files/a.mp4", 0, 45, title="s1", viral_score=7)

        clips = await database.get_all_clips()
        mine = [c for c in clips if c["project_id"] == pid]
        assert len(mine) == 1
        assert mine[0]["project_title"] == "My Podcast"
        assert mine[0]["viral_score"] == 7
        await database.delete_project(pid)

    asyncio.run(run())
