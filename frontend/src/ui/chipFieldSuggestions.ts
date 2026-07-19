export const filterChipSuggestions = (
  suggestions: string[],
  selectedValues: string[],
  query: string,
  limit = 100,
): string[] => {
  const trimmedQuery = query.trim();
  const normalizedQuery = trimmedQuery.toLocaleLowerCase();
  const selected = new Set(
    selectedValues.map((value) => value.toLocaleLowerCase()),
  );
  const seen = new Set(selected);
  const matches: string[] = [];
  let exactMatch: string | undefined;

  for (const suggestion of suggestions) {
    const normalizedSuggestion = suggestion.toLocaleLowerCase();
    if (
      seen.has(normalizedSuggestion) ||
      (normalizedQuery && !normalizedSuggestion.includes(normalizedQuery))
    ) {
      continue;
    }

    seen.add(normalizedSuggestion);
    if (normalizedQuery && normalizedSuggestion === normalizedQuery) {
      exactMatch = suggestion;
    } else {
      matches.push(suggestion);
    }
  }

  if (!trimmedQuery) {
    return matches.slice(0, limit);
  }

  if (exactMatch !== undefined) {
    return [exactMatch, ...matches].slice(0, limit);
  }

  return (
    selected.has(normalizedQuery) ? matches : [trimmedQuery, ...matches]
  ).slice(0, limit);
};
