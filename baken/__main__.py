from dataclasses import dataclass, field
from enum import Enum, auto, StrEnum
from pathlib import Path
import re
import sqlite3
import pprint

import questionary
from selenium import webdriver
from bs4 import BeautifulSoup
import requests

RACE_SEARCH_DETAIL_SITEURL = r"https://db.netkeiba.com/?pid=race_search_detail"
UPCOMING_AND_RECENT_RACE_LIST_SITEURL = r"https://race.netkeiba.com/top/race_list.html"


class TrackSurface(StrEnum):
    DIRT = "ダ"
    TURF = "芝"


class Weather(Enum):
    SUNNY = auto()
    CLOUDY = auto()
    RAINY = auto()


class TrackCondition(Enum):
    GOOD = auto()  # 良
    FIRM = auto()  # 稍重
    SOFT = auto()  # 重
    HEAVY = auto()  # 不良


@dataclass
class RaceInfo:
    course: str | None = None
    track_surface: TrackSurface | None = None
    distance_in_meters: int | None = None
    track_condition: TrackCondition | None = None
    weather: Weather | None = None
    entries: list["HorseEntry"] = field(default_factory=list)

    # 勝率を計算するメソッド
    def calc_win_rate(self) -> float:
        # 単勝人気順に勝率が定義されたタプル
        win_rate_values_by_popularity = (
            0.328,
            0.19,
            0.133,
            0.092,
            0.075,
            0.055,
            0.038,
            0.031,
            0.022,
            0.012,
            0.013,
            0.009,
            0.007,
            0.0001,
            0.002,
            0.001,
            0.0001,
            0.0001,
        )
        sorted_entries: tuple[HorseEntry] = tuple(
            sorted(self.entries, key=lambda x: x.odds)
        )
        for popularity, (entry, win_rate_by_popularity) in enumerate(
            zip(sorted_entries, win_rate_values_by_popularity)
        ):
            print(
                f"{popularity}番人気の勝率={win_rate_by_popularity} {entry.horse.name} オッズ：{entry.odds} 期待値={entry.odds * win_rate_by_popularity}"
            )


class TrainingCenter(StrEnum):
    RITTO = "栗東"
    MIHO = "美浦"


@dataclass
class Trainer:
    name: str
    training_center: TrainingCenter


@dataclass
class Horse:
    name: str
    age: int
    trainer: Trainer | None = None


@dataclass
class Horses:
    horses: list[Horse] = field(default_factory=list)


@dataclass
class HorseEntry:
    horse: Horse
    post_position: int | None = None
    weight: int | None = None
    odds: float | None = None
    jockey: str | None = None
    factors: dict = field(default_factory=dict)


def prepare_database(con: sqlite3.Connection):
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS horse (
        netkeiba_horse_id TEXT PRIMARY KEY,
        name TEXT,
        birth_date TEXT,
        lgt TEXT,
        sire_netkeiba_horse_id TEXT,
        dam_netkeiba_horse_id TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS race_program (
        netkeiba_race_id TEXT PRIMARY KEY,
        race_name TEXT,
        course TEXT,
        distance INTEGER,
        track_surface TEXT,
        race_date TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS race_card (
        netkeiba_race_id TEXT,
        post_position INTEGER,
        netkeiba_horse_id TEXT,
        weight_to_carry INTEGER,
        netkeiba_jockey_id TEXT,
        weight INTEGER,
        weight_change INTEGER,
        odds REAL,
        PRIMARY KEY (netkeiba_race_id, post_position),
        FOREIGN KEY (netkeiba_race_id) REFERENCES race_program(netkeiba_race_id),
        FOREIGN KEY (netkeiba_horse_id) REFERENCES horse(netkeiba_horse_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS past_performance (
        netkeiba_horse_id TEXT,
        netkeiba_race_id TEXT,
        finish_position INTEGER,
        finish_time TEXT,
        final_3f TEXT,
        PRIMARY KEY (netkeiba_horse_id, netkeiba_race_id),
        FOREIGN KEY (netkeiba_horse_id) REFERENCES horse(netkeiba_horse_id),
        FOREIGN KEY (netkeiba_race_id) REFERENCES race_program(netkeiba_race_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jockey (
        netkeiba_jockey_id TEXT PRIMARY KEY,
        name TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trainer (
        netkeiba_trainer_id TEXT PRIMARY KEY,
        name TEXT,
        training_center TEXT
    )
    """)
    con.commit()
    cur.close()


def old_cli():
    con = sqlite3.connect(Path("horse_racing.db"))
    prepare_database(con)
    print(
        f"レース詳細検索url：{RACE_SEARCH_DETAIL_SITEURL} 直近レース一覧url:{UPCOMING_AND_RECENT_RACE_LIST_SITEURL}"
    )
    print("helpを入力すると 使い方を表示、exitを入力すると 終了")
    print("調べたいレースのnetkeibaでの`race_id`を入力してください")

    while True:
        userinput = input("> ")
        if userinput == "help":
            print("使い方：race_idを調べて入力してください。")
            print(
                "上記urlから出馬表・レース結果等を参照すると、そのページのurlから見つけることができます。"
            )
            print(r"例1：https://db.netkeiba.com/race/レースID/")
            print(r"例2:https://race.netkeiba.com/race/shutuba.html?race_id=レースID")
            continue
        if userinput == "exit":
            break
        else:
            # レース結果が存在する（開催済みであり、反映されている）か確認する
            # 正規表現による書式で判定
            # -- TODO --

            # スクレイピング対象テーブルの存在で判定
            result_url = (
                rf"https://race.netkeiba.com/race/result.html?race_id={userinput}"
            )
            shutuba_url = (
                rf"https://race.netkeiba.com/race/shutuba.html?race_id={userinput}"
            )
            driver = webdriver.Firefox()
            driver.implicitly_wait(10)
            driver.get(result_url)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            driver.quit()
            # レース開催済みであるか調べる
            table = soup.select_one("table#All_Result_Table")
            if table:
                print(f"レースID {userinput} の結果が出ています。")
                cur = con.cursor()
                for row in table.select_one("tbody").select("tr.HorseList"):
                    # print(row)
                    # print("---")
                    netkeiba_horse_id = row.select_one(".Horse_Info a")["href"].split(
                        "/"
                    )[-1]
                    finish_time, margin, final_3f = [
                        timehtml.get_text().strip() for timehtml in row.select(".Time")
                    ]
                    horse_name = row.select_one(".Horse_Info").get_text().strip()
                    lgt = row.select_one(".Lgt_Txt").get_text().strip()[0]
                    print(
                        horse_name,
                        lgt,
                        row.select_one(".JockeyWeight").get_text().strip(),
                        row.select_one(".Jockey").get_text().strip(),
                        finish_time,
                        margin,
                        row.select_one(".Odds").get_text().strip(),
                        final_3f,
                        row.select_one(".Trainer").get_text().strip(),
                        row.select_one(".Weight").get_text().strip(),
                    )
                    cur.execute(
                        """
                    INSERT INTO horse (netkeiba_horse_id, name, lgt)
                    VALUES (?, ?, ?)
                    ON CONFLICT(netkeiba_horse_id) DO UPDATE SET
                        name = excluded.name,
                        lgt = excluded.lgt
                    """,
                        (netkeiba_horse_id, horse_name, lgt),
                    )
            else:
                print(f"レースID {userinput} は結果確定前です。")
                driver = webdriver.Firefox()
                driver.implicitly_wait(10)
                driver.get(shutuba_url)
                driver.quit()
            cur = con.cursor()

            cur.close()
            break
    con.close()


def cli():
    con = sqlite3.connect(Path("horse_racing.db"))
    prepare_database(con)
    while True:
        userinput = questionary.select(
            "",
            instruction="（矢印キーで選択）",
            choices=[
                {"name": "予想モード", "value": "analysis_mode"},
                {
                    "name": "レース番組登録モード",
                    "value": "race_data_registration_mode",
                },
                {"name": "終了", "value": "exit"},
            ],
        ).ask()
        match userinput:
            case "exit":
                break
            case "analysis_mode":
                print("予想モード")
            case "race_data_registration_mode":
                race_id = questionary.text("race_idを入力してください").ask()
                driver = webdriver.Firefox()
                driver.implicitly_wait(10)
                # 出馬表のhtmlを取得
                driver.get(
                    f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
                )
                soup = BeautifulSoup(driver.page_source.encode("utf-8"), "html.parser")
                driver.quit()
                table = soup.select_one("table.Shutuba_Table")
                cur = con.cursor()
                table_from_scrapes = []
                for row in table.find("tbody").find_all("tr"):
                    cells = [cell.get_text().strip() for cell in row.select("td")]
                    post_position = cells[1]
                    horse_name = cells[3]
                    horse_id = (
                        row.select_one(".HorseName").find("a")["href"].split("/")[-1]
                    )
                    lgt = cells[4][0]
                    weight_to_carry = cells[5]
                    jockey_name = cells[6]
                    jockey_id = (
                        row.select_one(".Jockey").find("a")["href"].split("/")[-2]
                    )
                    trainer = cells[7]
                    trainer_id = (
                        row.select_one(".Trainer").find("a")["href"].split("/")[-2]
                    )
                    weight = cells[8]
                    weight, weight_change = cells[8].split("(")
                    weight_change = weight_change.replace(")", "")
                    odds = cells[9]
                    print(
                        post_position,
                        horse_name,
                        horse_id,
                        lgt,
                        weight_to_carry,
                        jockey_name,
                        jockey_id,
                        trainer,
                        trainer_id,
                        weight,
                        weight_change,
                        odds,
                    )
                # cur.execute(
                #     "INSERT INTO race_card(netkeiba_race_id, post_position, netkeiba_horse_id, weight_to_carry, netkeiba_jockey_id, weight, weight_change, odds)",
                #     race_id,
                #     post_position,
                #     horse_id,
                #     weight_to_carry,
                #     jockey_id,
                #     weight,
                #     weight_change,
                #     odds
                # )
                # print(table_from_scrapes)
                # pprint.pprint(table_from_scrapes)
                # post_position = row.select_one("td.Umaban1").get_text().strip()
                # lgt_and_age = row.select_one("td.Barei").get_text().strip()
                # horse_name = row.select_one("td.HorseInfo .HorseName").get_text().strip()
                # jockey_name = row.select_one("td.Jockey").get_text().strip()
                # trainer_name = row.select_one("td.Trainer").get_text().strip()
                # weight = row.select_one("td.Weight").get_text().strip()
                # horse_id = row.select_one("td.HorseInfo a")["href"].split("/")[-1]
                # print(
                #     horse_name,
                #     jockey_name,
                #     trainer_name,
                #     horse_id,
                # )
                # race_program = cur.fetchall()
                # print("---")
                # print(race_program)
                # print("---")
                # -- TODO -- レースIDの結果反映チェック
    con.close()


if __name__ == "__main__":
    cli()
