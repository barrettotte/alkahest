package Alkahest::Editions;

# Parse complete book structures and enforce scope, format, and access policy.
use strict;
use warnings;
use Exporter qw(import);
use JSON::PP qw(decode_json);

our @EXPORT_OK = qw(
  edition_paths edition_source_ids load_editions render_book_structure
  structure_source_ids
);

sub _fail {
  die "error: $_[0]\n";
}

sub _set_equal {
  my ($left, $right) = @_;
  return 0 if @$left != @$right;
  my %left = map { $_ => 1 } @$left;
  return !grep { !$left{$_} } @$right;
}

sub _structure_ids {
  my ($registry, $structure_name) = @_;
  my $structure = $registry->{structures}{$structure_name}
    or _fail("unknown edition structure '$structure_name'");
  my @ids;
  for my $item (@{ $structure->{chapters} }) {
    if (exists $item->{source}) {
      push @ids, $item->{source};
    } else {
      push @ids, @{ $item->{sources} };
    }
  }
  for my $group (@{ $structure->{appendices} }) {
    push @ids, @{ $group->{sources} };
  }
  return @ids;
}

sub structure_source_ids {
  my ($registry, $structure_name) = @_;
  return _structure_ids($registry, $structure_name);
}

sub edition_source_ids {
  my ($registry, $edition_name) = @_;
  my $edition = $registry->{editions}{$edition_name}
    or _fail("unknown edition '$edition_name'");
  return _structure_ids($registry, $edition->{structure});
}

sub edition_paths {
  my ($registry, $edition_name) = @_;
  return map { $registry->{sources}{$_}{path} }
    edition_source_ids($registry, $edition_name);
}

sub _render_items {
  my ($registry, $items, $indent) = @_;
  my $output = '';
  for my $item (@$items) {
    if (exists $item->{source}) {
      $output .= (' ' x $indent) . '- '
        . $registry->{sources}{ $item->{source} }{path} . "\n";
      next;
    }
    $output .= (' ' x $indent) . qq{- part: "$item->{part}"\n};
    $output .= (' ' x ($indent + 2)) . "chapters:\n";
    for my $source_id (@{ $item->{sources} }) {
      $output .= (' ' x ($indent + 4)) . '- '
        . $registry->{sources}{$source_id}{path} . "\n";
    }
  }
  return $output;
}

sub render_book_structure {
  my ($registry, $edition_name) = @_;
  my $edition = $registry->{editions}{$edition_name}
    or _fail("unknown edition '$edition_name'");
  my $structure = $registry->{structures}{ $edition->{structure} };
  my $output = "  chapters:\n";
  $output .= _render_items($registry, $structure->{chapters}, 4);
  $output .= "  appendices:\n";
  for my $group (@{ $structure->{appendices} }) {
    $output .= qq{    - part: "$group->{part}"\n      chapters:\n};
    for my $source_id (@{ $group->{sources} }) {
      $output .= "        - $registry->{sources}{$source_id}{path}\n";
    }
  }
  $output .= "\n";
  return $output;
}

sub load_editions {
  my ($path) = @_;
  open my $handle, '<:raw', $path
    or _fail("cannot read edition manifest $path: $!");
  local $/;
  my $content = <$handle>;
  close $handle;
  my $registry = eval { decode_json($content) };
  _fail("invalid edition manifest JSON: $@") if !$registry;
  _fail('edition manifest version must be 1')
    if ($registry->{version} // 0) != 1;

  my @required_editions = qw(
    abridged epub full preview print private public supplemental web
  );
  my @required_structures = qw(abridged full preview private supplemental web);
  my @actual_editions = sort keys %{ $registry->{editions} // {} };
  my @actual_structures = sort keys %{ $registry->{structures} // {} };
  _fail('editions must be exactly: ' . join(', ', @required_editions))
    if !_set_equal(\@actual_editions, \@required_editions);
  _fail('edition structures must be exactly: ' . join(', ', @required_structures))
    if !_set_equal(\@actual_structures, \@required_structures);

  my %valid_role = map { $_ => 1 } qw(front chapter back appendix);
  my %valid_availability = map { $_ => 1 } qw(core online-only supplemental private);
  my %valid_format = map { $_ => 1 } qw(html epub typst latex);
  my %path_owner;
  for my $source_id (sort keys %{ $registry->{sources} // {} }) {
    _fail("invalid edition source ID '$source_id'")
      if $source_id !~ /^[a-z][a-z0-9-]*$/;
    my $source = $registry->{sources}{$source_id};
    _fail("edition source '$source_id' must be an object")
      if ref($source) ne 'HASH';
    my $source_path = $source->{path} // '';
    _fail("invalid edition source path for '$source_id'")
      if $source_path !~ m{^(?:[a-z0-9][a-z0-9-]*/)*[a-z0-9][a-z0-9-]*\.qmd$};
    _fail("edition source path '$source_path' is registered more than once")
      if $path_owner{$source_path}++;
    _fail("edition source '$source_id' has invalid role")
      if !$valid_role{ $source->{role} // '' };
    _fail("edition source '$source_id' has invalid availability")
      if !$valid_availability{ $source->{availability} // '' };
    _fail("edition source '$source_id' must declare formats")
      if ref($source->{formats}) ne 'ARRAY' || !@{ $source->{formats} };
    my %seen_format;
    for my $format (@{ $source->{formats} }) {
      _fail("edition source '$source_id' has unsupported format '$format'")
        if !$valid_format{$format};
      _fail("edition source '$source_id' repeats format '$format'")
        if $seen_format{$format}++;
    }
    _fail("non-core source '$source_id' must be an appendix or private chapter")
      if $source->{availability} ne 'core'
        && !($source->{role} eq 'appendix'
          || ($source->{availability} eq 'private' && $source->{role} eq 'chapter'));
  }
  _fail('edition manifest has no sources')
    if !keys %{ $registry->{sources} // {} };

  my %structure_sets;
  for my $structure_name (@required_structures) {
    my $structure = $registry->{structures}{$structure_name};
    _fail("structure '$structure_name' must have chapters and appendices arrays")
      if ref($structure->{chapters}) ne 'ARRAY'
        || !@{ $structure->{chapters} }
        || ref($structure->{appendices}) ne 'ARRAY';
    my (%selected, %parts);
    for my $item (@{ $structure->{chapters} }) {
      _fail("structure '$structure_name' has an invalid chapter item")
        if ref($item) ne 'HASH';
      my @ids;
      if (exists $item->{source}) {
        _fail("structure '$structure_name' direct chapter item is malformed")
          if keys(%$item) != 1;
        @ids = ($item->{source});
      } else {
        my $part = $item->{part} // '';
        _fail("structure '$structure_name' has an invalid or duplicate part")
          if $part !~ /^[A-Za-z][A-Za-z0-9 -]*$/ || $parts{$part}++;
        _fail("structure '$structure_name' part '$part' has no sources")
          if ref($item->{sources}) ne 'ARRAY' || !@{ $item->{sources} };
        @ids = @{ $item->{sources} };
      }
      for my $source_id (@ids) {
        _fail("structure '$structure_name' references unknown source '$source_id'")
          if !exists $registry->{sources}{$source_id};
        _fail("structure '$structure_name' puts appendix '$source_id' in chapters")
          if $registry->{sources}{$source_id}{role} eq 'appendix';
        _fail("structure '$structure_name' repeats source '$source_id'")
          if $selected{$source_id}++;
      }
    }
    for my $group (@{ $structure->{appendices} }) {
      my $part = $group->{part} // '';
      _fail("structure '$structure_name' has an invalid or duplicate appendix part")
        if $part !~ /^[A-Za-z][A-Za-z0-9 -]*$/ || $parts{$part}++;
      _fail("structure '$structure_name' appendix part '$part' has no sources")
        if ref($group->{sources}) ne 'ARRAY' || !@{ $group->{sources} };
      for my $source_id (@{ $group->{sources} }) {
        _fail("structure '$structure_name' references unknown appendix '$source_id'")
          if !exists $registry->{sources}{$source_id};
        _fail("structure '$structure_name' puts non-appendix '$source_id' in appendices")
          if $registry->{sources}{$source_id}{role} ne 'appendix';
        _fail("structure '$structure_name' repeats source '$source_id'")
          if $selected{$source_id}++;
      }
    }
    $structure_sets{$structure_name} = \%selected;
  }

  my %expected_edition = (
    full => ['full', 'public', [qw(html epub typst latex)]],
    abridged => ['abridged', 'public', [qw(html epub typst latex)]],
    preview => ['preview', 'public', [qw(html)]],
    print => ['full', 'public', [qw(typst latex)]],
    epub => ['full', 'public', [qw(epub)]],
    web => ['web', 'public', [qw(html)]],
    public => ['full', 'public', [qw(html epub typst latex)]],
    private => ['private', 'private', [qw(html)]],
    supplemental => ['supplemental', 'public', [qw(html)]],
  );
  for my $edition_name (@required_editions) {
    my ($structure, $access, $formats) = @{ $expected_edition{$edition_name} };
    my $edition = $registry->{editions}{$edition_name};
    _fail("edition '$edition_name' must use structure '$structure'")
      if ($edition->{structure} // '') ne $structure;
    _fail("edition '$edition_name' must have access '$access'")
      if ($edition->{access} // '') ne $access;
    _fail("edition '$edition_name' has invalid formats")
      if ref($edition->{formats}) ne 'ARRAY'
        || !_set_equal($edition->{formats}, $formats);
    for my $source_id (keys %{ $structure_sets{$structure} }) {
      my %allowed = map { $_ => 1 } @{ $registry->{sources}{$source_id}{formats} };
      for my $format (@{ $edition->{formats} }) {
        _fail("edition '$edition_name' selects '$source_id', which does not support $format")
          if !$allowed{$format};
      }
      _fail("public edition '$edition_name' includes private source '$source_id'")
        if $access eq 'public'
          && $registry->{sources}{$source_id}{availability} eq 'private';
    }
  }

  my %availability_sets;
  for my $availability (keys %valid_availability) {
    $availability_sets{$availability} = {
      map { $_ => 1 } grep {
        $registry->{sources}{$_}{availability} eq $availability
      } keys %{ $registry->{sources} }
    };
  }
  for my $pair (
    ['full', [qw(core)]],
    ['web', [qw(core online-only)]],
    ['supplemental', [qw(core supplemental)]],
    ['private', [qw(core private)]],
  ) {
    my ($structure, $classes) = @$pair;
    my %expected;
    for my $class (@$classes) {
      @expected{keys %{ $availability_sets{$class} }} =
        (1) x keys(%{ $availability_sets{$class} });
    }
    my @actual = sort keys %{ $structure_sets{$structure} };
    my @wanted = sort keys %expected;
    _fail("structure '$structure' does not select exactly its allowed availability classes")
      if !_set_equal(\@actual, \@wanted);
  }
  for my $structure (qw(abridged preview)) {
    for my $source_id (keys %{ $structure_sets{$structure} }) {
      _fail("structure '$structure' includes exceptional source '$source_id'")
        if $registry->{sources}{$source_id}{availability} ne 'core';
    }
    _fail("structure '$structure' must be a nonempty proper subset of full")
      if !keys %{ $structure_sets{$structure} }
        || keys(%{ $structure_sets{$structure} }) >= keys(%{ $structure_sets{full} });
  }
  my $preview_chapters = grep {
    $registry->{sources}{$_}{role} eq 'chapter'
  } keys %{ $structure_sets{preview} };
  my $abridged_chapters = grep {
    $registry->{sources}{$_}{role} eq 'chapter'
  } keys %{ $structure_sets{abridged} };
  my $full_chapters = grep {
    $registry->{sources}{$_}{role} eq 'chapter'
  } keys %{ $structure_sets{full} };
  _fail('preview structure must contain one or two manuscript chapters')
    if $preview_chapters < 1 || $preview_chapters > 2;
  _fail('abridged structure must contain more chapters than preview and fewer than full')
    if $abridged_chapters <= $preview_chapters
      || $abridged_chapters >= $full_chapters;

  return $registry;
}

1;
