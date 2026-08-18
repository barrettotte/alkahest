package Alkahest::AppendixEditions;

# Parse and validate the explicit appendix-edition registry shared by build tools.
use strict;
use warnings;
use Exporter qw(import);
use JSON::PP qw(decode_json);

our @EXPORT_OK = qw(edition_paths load_appendix_editions);

sub _fail {
  die "error: $_[0]\n";
}

sub _set_equal {
  my ($left, $right) = @_;
  return 0 if @$left != @$right;
  my %left = map { $_ => 1 } @$left;
  return !grep { !$left{$_} } @$right;
}

sub edition_paths {
  my ($registry, $edition_name) = @_;
  my $edition = $registry->{editions}{$edition_name}
    or _fail("unknown appendix edition '$edition_name'");
  my @paths;
  for my $group (@{ $edition->{groups} }) {
    push @paths, map { $registry->{sources}{$_}{path} } @{ $group->{chapters} };
  }
  return @paths;
}

sub load_appendix_editions {
  my ($path) = @_;
  open my $handle, '<:raw', $path
    or _fail("cannot read appendix edition registry $path: $!");
  local $/;
  my $content = <$handle>;
  close $handle;
  my $registry = eval { decode_json($content) };
  _fail("invalid appendix edition registry JSON: $@") if !$registry;
  _fail("appendix edition registry version must be 1")
    if ($registry->{version} // 0) != 1;

  my @required_editions = qw(epub full html preview print supplemental);
  my @actual_editions = sort keys %{ $registry->{editions} // {} };
  _fail("appendix editions must be exactly: " . join(', ', @required_editions))
    if !_set_equal(\@actual_editions, \@required_editions);

  my %valid_availability = map { $_ => 1 } qw(core online-only supplemental);
  my %path_owner;
  for my $source_id (sort keys %{ $registry->{sources} // {} }) {
    _fail("invalid appendix source ID '$source_id'")
      if $source_id !~ /^[a-z][a-z0-9-]*$/;
    my $source = $registry->{sources}{$source_id};
    my $source_path = $source->{path} // '';
    _fail("invalid appendix path for '$source_id'")
      if $source_path !~ m{^appendices/[a-z0-9][a-z0-9-]*\.qmd$};
    _fail("appendix path '$source_path' is assigned to more than one source")
      if $path_owner{$source_path}++;
    my $availability = $source->{availability} // '';
    _fail("unsupported availability '$availability' for '$source_id'")
      if !$valid_availability{$availability};
  }
  _fail("appendix edition registry has no sources")
    if !keys %{ $registry->{sources} // {} };

  my %expected_formats = (
    full => [qw(html epub typst latex)],
    preview => [qw(html)],
    print => [qw(typst latex)],
    epub => [qw(epub)],
    html => [qw(html)],
    supplemental => [qw(html)],
  );
  my %selected_by_edition;
  for my $edition_name (@required_editions) {
    my $edition = $registry->{editions}{$edition_name};
    _fail("edition '$edition_name' has invalid formats")
      if ref($edition->{formats}) ne 'ARRAY'
        || !_set_equal($edition->{formats}, $expected_formats{$edition_name});
    _fail("edition '$edition_name' has no appendix groups")
      if ref($edition->{groups}) ne 'ARRAY' || !@{ $edition->{groups} };
    my (%parts, %selected);
    for my $group (@{ $edition->{groups} }) {
      my $part = $group->{part} // '';
      _fail("edition '$edition_name' has an invalid appendix group title")
        if $part !~ /^[A-Za-z][A-Za-z0-9 -]*$/;
      _fail("edition '$edition_name' repeats appendix group '$part'")
        if $parts{$part}++;
      _fail("edition '$edition_name' group '$part' has no chapters")
        if ref($group->{chapters}) ne 'ARRAY' || !@{ $group->{chapters} };
      for my $source_id (@{ $group->{chapters} }) {
        _fail("edition '$edition_name' references unknown appendix '$source_id'")
          if !exists $registry->{sources}{$source_id};
        _fail("edition '$edition_name' selects appendix '$source_id' more than once")
          if $selected{$source_id}++;
      }
    }
    $selected_by_edition{$edition_name} = \%selected;
  }

  my @core = sort grep {
    $registry->{sources}{$_}{availability} eq 'core'
  } keys %{ $registry->{sources} };
  my @online = sort grep {
    $registry->{sources}{$_}{availability} eq 'online-only'
  } keys %{ $registry->{sources} };
  my @supplemental = sort grep {
    $registry->{sources}{$_}{availability} eq 'supplemental'
  } keys %{ $registry->{sources} };
  _fail("registry must contain core, online-only, and supplemental appendices")
    if !@core || !@online || !@supplemental;

  for my $edition_name (qw(full print epub)) {
    my @selected = sort keys %{ $selected_by_edition{$edition_name} };
    _fail("edition '$edition_name' must select exactly the core appendices")
      if !_set_equal(\@selected, \@core);
  }
  my @html_selected = sort keys %{ $selected_by_edition{html} };
  my @html_expected = sort (@core, @online);
  _fail("edition 'html' must select core and online-only appendices")
    if !_set_equal(\@html_selected, \@html_expected);
  my @supp_selected = sort keys %{ $selected_by_edition{supplemental} };
  my @supp_expected = sort (@core, @supplemental);
  _fail("edition 'supplemental' must select core and supplemental appendices")
    if !_set_equal(\@supp_selected, \@supp_expected);
  my @preview_selected = sort keys %{ $selected_by_edition{preview} };
  _fail("edition 'preview' must select a nonempty proper subset of core appendices")
    if !@preview_selected || @preview_selected >= @core
      || grep { $registry->{sources}{$_}{availability} ne 'core' } @preview_selected;

  return $registry;
}

1;
