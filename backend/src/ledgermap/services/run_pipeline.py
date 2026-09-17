from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from ledgermap.domain.models import AccountNode, MappingCandidate, SourceType
from ledgermap.services.matching import resolve_name
from ledgermap.services.source_detection import detect_source_type
from ledgermap.services.tb_parser import parse_rows
from ledgermap.services.workbook_reader import read_mapping_memory, read_trial_balance


@dataclass(frozen=True)
class ProcessedLineItem:
	node: AccountNode
	candidate: MappingCandidate


@dataclass(frozen=True)
class RunPreview:
	source_type: SourceType
	line_items: list[ProcessedLineItem]

	@property
	def resolved_rows(self) -> int:
		return sum(item.candidate.code is not None for item in self.line_items)


def process_workbook(
	source: str | Path | bytes | BinaryIO,
	*,
	mapping_source: str | Path | bytes | BinaryIO | None = None,
) -> RunPreview:
	rows = read_trial_balance(source)
	nodes = parse_rows(rows)
	mappings = read_mapping_memory(mapping_source or source)
	source_type = detect_source_type(
		headers=("Particulars", "Opening", "Closing"),
		account_codes=(row.code for row in rows),
	)
	line_items: list[ProcessedLineItem] = []
	for node in nodes:
		if node.is_group:
			continue
		candidate = resolve_name(node.name, mappings)
		line_items.append(ProcessedLineItem(node=node, candidate=candidate))
	return RunPreview(source_type=source_type, line_items=line_items)