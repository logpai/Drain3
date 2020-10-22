"""
Description : A simple section-based performance profiler
Author      : David Ohana
Author_email: david.ohana@ibm.com
License     : MIT
"""
import time

from abc import ABC, abstractmethod


class Profiler(ABC):

    @abstractmethod
    def start_section(self, section_name: str):
        pass

    @abstractmethod
    def end_section(self):
        pass

    @abstractmethod
    def report(self, report_internal_sec=30):
        pass

    @abstractmethod
    def print_results(self):
        pass


class NullProfiler(Profiler):
    def start_section(self, section_name: str):
        pass

    def end_section(self):
        pass

    def report(self, report_internal_sec=30):
        pass

    def print_results(self):
        pass


class SimpleProfiler(Profiler):
    def __init__(self):
        self.section_to_stats = {}
        self.current_section_name = ""
        self.current_section_start_time_sec = 0
        self.last_report_timestamp = time.time()

    def start_section(self, section_name: str):
        if not section_name:
            raise ValueError("Section name is empty")
        if self.current_section_name:
            self.end_section()
        self.current_section_name = section_name
        self.current_section_start_time_sec = time.time()

    def end_section(self):
        if not self.current_section_name:
            raise ValueError("Not inside a section")
        took_sec = time.time() - self.current_section_start_time_sec
        current_section = self.section_to_stats.get(self.current_section_name, None)
        if current_section is None:
            current_section = ProfiledSectionStats(self.current_section_name)
            self.section_to_stats[self.current_section_name] = current_section

        current_section.sample_count += 1
        current_section.total_time_sec += took_sec

        self.current_section_name = ""
        self.current_section_start_time_sec = 0

    def report(self, report_internal_sec=30):
        if time.time() - self.last_report_timestamp > report_internal_sec:
            self.print_results()
            self.last_report_timestamp = time.time()

    def print_results(self):
        sections = self.section_to_stats.values()
        all_sections_time_sec = sum(map(lambda it: it.total_time_sec, sections))
        all_section_sample_count = sum(map(lambda it: it.sample_count, sections))
        all_section = ProfiledSectionStats("Total", all_section_sample_count, all_sections_time_sec)
        print(f"{SimpleProfiler.__name__}: {all_section.to_string(all_sections_time_sec)}")
        sorted_sections = sorted(sections, key=lambda it: it.total_time_sec, reverse=True)
        for section in sorted_sections:
            print(f"{SimpleProfiler.__name__}: {section.to_string(all_sections_time_sec)}")


class ProfiledSectionStats:
    def __init__(self, section_name, sample_count=0, total_time_sec=0):
        self.section_name = section_name
        self.sample_count = sample_count
        self.total_time_sec = total_time_sec

    def to_string(self, sum_time_sec: int):
        percent = 100 * self.total_time_sec / sum_time_sec
        rate = 1000 * self.total_time_sec / self.sample_count
        return f"{self.section_name: <15}: took {self.total_time_sec:>7.2f} sec ({percent:>6.2f}%), " \
               f"{self.sample_count: <10} samples, " \
               f"{rate: 7.2f} ms per 1K samples"
