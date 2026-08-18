package Alkahest::Identities;

# Discover and validate stable manuscript, registry, and companion-asset IDs.
use strict;
use warnings;
use Cwd qw(abs_path);
use Exporter qw(import);
use File::Find qw(find);
use JSON::PP qw(decode_json);

our @EXPORT_OK = qw(
  add_companion_assets canonical_variant identity_key inventory_book load_identity_policy load_json_file
  validate_edition_manifests validate_language_variants validate_migrations
);

sub _fail {
  die "error: $_[0]\n";
}

sub load_json_file {
  my ($path, $label) = @_;
  open my $handle, '<:raw', $path
    or _fail("cannot read $label $path: $!");
  local $/;
  my $content = <$handle>;
  close $handle;
  my $value = eval { decode_json($content) };
  _fail("invalid $label JSON in $path: $@") if !$value;
  return $value;
}

sub load_identity_policy {
  my ($path) = @_;
  my $policy = load_json_file($path, 'identity policy');
  _fail('identity policy version must be 1')
    if ($policy->{version} // 0) != 1;
  _fail('identity policy book_id must be a stable lowercase ID')
    if ($policy->{book_id} // '') !~ /^[a-z][a-z0-9-]*$/;
  _fail('identity policy canonical_language must be a BCP 47 tag')
    if ($policy->{canonical_language} // '')
      !~ /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/;
  _fail('identity policy language_variants must be a nonempty array')
    if ref($policy->{language_variants}) ne 'ARRAY'
      || !@{ $policy->{language_variants} };
  _fail('identity policy edition_manifests must be an array')
    if ref($policy->{edition_manifests}) ne 'ARRAY';
  _fail('identity policy companion_assets must be an object')
    if ref($policy->{companion_assets}) ne 'HASH';
  _fail('identity policy migrations must be an array')
    if ref($policy->{migrations}) ne 'ARRAY';
  return $policy;
}

sub identity_key {
  my ($record) = @_;
  return "$record->{namespace}\0$record->{id}";
}

sub _add_record {
  my ($records, $record) = @_;
  my $key = identity_key($record);
  if (my $previous = $records->{$key}) {
    _fail("duplicate $record->{namespace} identity '$record->{id}' in "
      . "$record->{source} and $previous->{source}");
  }
  $records->{$key} = $record;
}

sub _kind_for_content_id {
  my ($id) = @_;
  return 'figure'   if $id =~ /^fig-/;
  return 'table'    if $id =~ /^tbl-/;
  return 'equation' if $id =~ /^eq-/;
  return 'listing'  if $id =~ /^lst-/;
  return 'exercise' if $id =~ /^exr-/;
  return 'solution' if $id =~ /^sol-/;
  return 'anchor';
}

sub _reject_setext_headings {
  my ($lines, $source) = @_;
  my ($fence, $front_matter) = ('', 0);
  for my $index (0 .. $#$lines) {
    my $line = $lines->[$index];
    if ($index == 0 && $line =~ /^---\s*$/) {
      $front_matter = 1;
      next;
    }
    if ($front_matter) {
      $front_matter = 0 if $line =~ /^---\s*$/;
      next;
    }
    if ($fence ne '') {
      $fence = '' if $line =~ /^\Q$fence\E\s*$/;
      next;
    }
    if ($line =~ /^(`{3,}|~{3,})/) {
      $fence = $1;
      next;
    }
    next if $line !~ /^(?:={2,}|-{2,})\s*$/ || $index == 0;
    my $previous = $lines->[$index - 1];
    _fail("$source:" . ($index + 1)
      . ': Setext headings cannot carry the required explicit ID; use an ATX heading')
      if $previous =~ /\S/;
  }
}

sub _scan_qmd_file {
  my ($path, $source, $records) = @_;
  open my $handle, '<:encoding(UTF-8)', $path
    or _fail("cannot read manuscript source $path: $!");
  my @lines = <$handle>;
  close $handle;
  _reject_setext_headings(\@lines, $source);

  my ($fence, $executable_fence, $line_number) = ('', 0, 0);
  my @div_stack;
  for my $line (@lines) {
    ++$line_number;
    if ($fence ne '') {
      if ($line =~ /^\Q$fence\E\s*$/) {
        ($fence, $executable_fence) = ('', 0);
        next;
      }
      if ($executable_fence
          && $line =~ /^\s*(?:#|%%)\|\s*label:\s*([A-Za-z][A-Za-z0-9_.:-]*)\s*$/) {
        my $id = $1;
        _add_record($records, {
          namespace => 'content', id => $id,
          kind => _kind_for_content_id($id), source => $source,
          line => $line_number,
        });
      }
      next;
    }

    if ($line =~ /^(`{3,}|~{3,})(.*)$/) {
      my ($marker, $info) = ($1, $2);
      while ($info =~ /\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)/g) {
        my $id = $1;
        _add_record($records, {
          namespace => 'content', id => $id,
          kind => _kind_for_content_id($id), source => $source,
          line => $line_number,
        });
      }
      $fence = $marker;
      $executable_fence = $info =~ /\{(?:mermaid|dot|graphviz|python|r|julia)\b/ ? 1 : 0;
      next;
    }

    if ($line =~ /^:{3,}\s+\{([^}]*)\}\s*$/) {
      my $attributes = $1;
      my ($id) = $attributes =~ /#([A-Za-z][A-Za-z0-9_.:-]*)/;
      push @div_stack, $id // '';
    } elsif ($line =~ /^:{3,}\s*$/) {
      pop @div_stack if @div_stack;
    }

    if ($line =~ /^(#{1,6})\s+/) {
      my $level = length($1);
      my @ids = ($line =~ /\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)/g);
      my ($semantic_owner) = grep {
        /^(?:cau|cnj|cor|def|exm|exr|imp|lab|lem|nte|prp|project|sol|thm|tip|wrn)-/
      } reverse @div_stack;
      if (defined $semantic_owner) {
        _fail("$source:$line_number: a semantic block title must use its enclosing '$semantic_owner' identity, not a second heading ID")
          if @ids;
        next;
      }
      _fail("$source:$line_number: every heading must have exactly one explicit persistent ID")
        if @ids != 1;
      _add_record($records, {
        namespace => 'content', id => $ids[0],
        kind => $level == 1 ? 'chapter' : 'section', source => $source,
        line => $line_number,
      });
      next;
    }

    while ($line =~ /\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)/g) {
      my $id = $1;
      _add_record($records, {
        namespace => 'content', id => $id,
        kind => _kind_for_content_id($id), source => $source,
        line => $line_number,
      });
    }
    while ($line =~ /\bid=["']([A-Za-z][A-Za-z0-9_.:-]*)["']/g) {
      my $id = $1;
      _add_record($records, {
        namespace => 'content', id => $id,
        kind => _kind_for_content_id($id), source => $source,
        line => $line_number,
      });
    }
  }
  _fail("$source: unclosed fenced code block") if $fence ne '';
}

sub _yaml_mapping_keys {
  my ($path, $section, $namespace, $kind, $source, $records) = @_;
  open my $handle, '<:encoding(UTF-8)', $path
    or _fail("cannot read $namespace registry $path: $!");
  my ($inside, $found, $line_number) = (0, 0, 0);
  while (my $line = <$handle>) {
    ++$line_number;
    if (!$inside && $line =~ /^\Q$section\E:\s*$/) {
      ($inside, $found) = (1, 1);
      next;
    }
    next if !$inside;
    last if $line =~ /^\S/;
    next if $line =~ /^\s*(?:#.*)?$/;
    if ($line =~ /^  ([a-z][a-z0-9-]*):\s*$/) {
      _add_record($records, {
        namespace => $namespace, id => $1, kind => $kind,
        source => $source, line => $line_number,
      });
    }
  }
  close $handle;
  _fail("$source has no '$section' mapping") if !$found;
  my $count = grep { $_->{namespace} eq $namespace } values %$records;
  _fail("$source has no persistent $kind identities") if !$count;
}

sub _relative_path {
  my ($path, $root) = @_;
  $path =~ s{^\Q$root\E/?}{};
  $path =~ s{\\}{/}g;
  return $path;
}

sub inventory_book {
  my ($book_root, $policy, $variant) = @_;
  my $variant_root = $variant->{root} // '';
  _fail("invalid language-variant root '$variant_root'")
    if $variant_root ne '.'
      && $variant_root !~ m{^[a-zA-Z0-9][a-zA-Z0-9_./-]*$};
  _fail("language-variant root must not contain '..'")
    if $variant_root =~ m{(?:^|/)\.\.(?:/|$)};
  my $content_root = abs_path("$book_root/$variant_root")
    or _fail("language-variant root '$variant_root' does not exist");

  my @excluded_roots;
  for my $other (@{ $policy->{language_variants} }) {
    my $other_root_name = $other->{root} // '';
    next if $other_root_name eq $variant_root;
    my $other_root = abs_path("$book_root/$other_root_name");
    next if !defined $other_root;
    push @excluded_roots, $other_root
      if index($other_root, "$content_root/") == 0;
  }

  my %records;
  my @qmd;
  find(
    sub {
      return if !-f $_ || $_ !~ /\.qmd$/;
      my $path = $File::Find::name;
      return if $path =~ m{/(?:_build|_extensions|\.quarto)/};
      return if grep { index($path, "$_/") == 0 } @excluded_roots;
      push @qmd, $path;
    },
    $content_root,
  );
  _fail("language variant '$variant->{language}' contains no manuscript sources")
    if !@qmd;
  for my $path (sort @qmd) {
    my $source = _relative_path($path, $content_root);
    _scan_qmd_file($path, $source, \%records);
  }

  my $glossary = "$content_root/glossary.yml";
  my $index = "$content_root/index.yml";
  _fail("language variant '$variant->{language}' is missing glossary.yml")
    if !-f $glossary;
  _fail("language variant '$variant->{language}' is missing index.yml")
    if !-f $index;
  _yaml_mapping_keys($glossary, 'terms', 'glossary', 'glossary-term',
    'glossary.yml', \%records);
  _yaml_mapping_keys($index, 'entries', 'index', 'index-concept',
    'index.yml', \%records);

  return \%records;
}

sub _validate_variant_shape {
  my ($book_root, $policy) = @_;
  my (%languages, @canonical);
  for my $variant (@{ $policy->{language_variants} }) {
    _fail('each language variant must be an object') if ref($variant) ne 'HASH';
    my $language = $variant->{language} // '';
    _fail("invalid language-variant tag '$language'")
      if $language !~ /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/;
    _fail("duplicate language variant '$language'") if $languages{$language}++;
    my $mode = $variant->{mode} // '';
    _fail("unsupported language-variant mode '$mode'")
      if $mode !~ /^(?:canonical|shared-source|translated)$/;
    push @canonical, $variant if $mode eq 'canonical';
    my $root = $variant->{root} // '';
    _fail("invalid language-variant root '$root'")
      if $root ne '.' && $root !~ m{^[a-zA-Z0-9][a-zA-Z0-9_./-]*$};
    _fail("language-variant root '$root' must not contain '..'")
      if $root =~ m{(?:^|/)\.\.(?:/|$)};
    _fail("language-variant root '$root' does not exist")
      if !-d "$book_root/$root";
    if (defined $variant->{profile}) {
      my $profile = $variant->{profile};
      _fail("invalid language profile '$profile'")
        if $profile !~ /^_quarto-[a-zA-Z0-9-]+\.yml$/
          || !-f "$book_root/$profile";
      open my $profile_handle, '<:encoding(UTF-8)', "$book_root/$profile"
        or _fail("cannot read language profile '$profile'");
      my @profile_languages;
      while (my $line = <$profile_handle>) {
        push @profile_languages, $1
          if $line =~ /^lang:\s*([A-Za-z0-9-]+)\s*$/;
      }
      close $profile_handle;
      _fail("language profile '$profile' must declare lang: $language exactly once")
        if @profile_languages != 1 || $profile_languages[0] ne $language;
    }
    _fail("shared-source language '$language' needs an explicit locale profile")
      if $mode eq 'shared-source' && !defined $variant->{profile};
  }
  _fail('identity policy must declare exactly one canonical language variant')
    if @canonical != 1;
  _fail('canonical variant language must match canonical_language')
    if $canonical[0]{language} ne $policy->{canonical_language};
  return $canonical[0];
}

sub canonical_variant {
  my ($book_root, $policy) = @_;
  return _validate_variant_shape($book_root, $policy);
}

sub validate_language_variants {
  my ($book_root, $policy, $canonical_records) = @_;
  my $canonical = _validate_variant_shape($book_root, $policy);
  for my $variant (@{ $policy->{language_variants} }) {
    next if $variant->{mode} eq 'canonical';
    if ($variant->{mode} eq 'shared-source') {
      _fail("shared-source language '$variant->{language}' must use the canonical root")
        if $variant->{root} ne $canonical->{root};
      next;
    }
    my $translated = inventory_book($book_root, $policy, $variant);
    my %canonical_semantic = map {
      $_ => $canonical_records->{$_}{kind}
    } grep {
      $canonical_records->{$_}{namespace} ne 'asset'
    } keys %$canonical_records;
    my %translated_semantic = map {
      $_ => $translated->{$_}{kind}
    } keys %$translated;
    for my $key (sort keys %canonical_semantic) {
      my ($namespace, $id) = split /\0/, $key, 2;
      _fail("translation '$variant->{language}' is missing $namespace identity '$id'")
        if !exists $translated_semantic{$key};
      _fail("translation '$variant->{language}' changes the kind of $namespace identity '$id'")
        if $translated_semantic{$key} ne $canonical_semantic{$key};
    }
    for my $key (sort keys %translated_semantic) {
      my ($namespace, $id) = split /\0/, $key, 2;
      _fail("translation '$variant->{language}' adds unmatched $namespace identity '$id'")
        if !exists $canonical_semantic{$key};
    }
  }
  return $canonical;
}

sub add_companion_assets {
  my ($book_root, $policy, $records) = @_;
  my %paths;
  for my $id (sort keys %{ $policy->{companion_assets} }) {
    _fail("invalid companion-asset ID '$id'; expected asset-...")
      if $id !~ /^asset-[a-z][a-z0-9-]*$/;
    my $asset = $policy->{companion_assets}{$id};
    _fail("companion asset '$id' must be an object") if ref($asset) ne 'HASH';
    my $path = $asset->{path} // '';
    _fail("invalid companion-asset path for '$id'")
      if $path !~ m{^companion/[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)*$};
    _fail("companion-asset path '$path' is registered more than once")
      if $paths{$path}++;
    _fail("companion asset '$id' references missing file '$path'")
      if !-f "$book_root/$path";
    _fail("companion asset '$id' needs a media_type")
      if ($asset->{media_type} // '') !~ m{^[a-z0-9.+-]+/[a-z0-9.+-]+$}i;
    _fail("companion asset '$id' needs a concise description")
      if ($asset->{description} // '') !~ /\S/;
    _add_record($records, {
      namespace => 'asset', id => $id, kind => 'companion-asset',
      source => $path,
    });
  }
  _fail('identity policy must register at least one companion asset')
    if !keys %{ $policy->{companion_assets} };
}

sub validate_edition_manifests {
  my ($book_root, $policy, $records) = @_;
  for my $manifest_path (@{ $policy->{edition_manifests} }) {
    _fail("invalid edition-manifest path '$manifest_path'")
      if $manifest_path !~ /^[A-Za-z0-9][A-Za-z0-9_.-]*\.json$/;
    my $manifest = load_json_file("$book_root/$manifest_path", 'edition manifest');
    _fail("edition manifest '$manifest_path' must have source, structure, and edition objects")
      if ref($manifest->{sources}) ne 'HASH'
        || ref($manifest->{structures}) ne 'HASH'
        || ref($manifest->{editions}) ne 'HASH';
    for my $source_id (sort keys %{ $manifest->{sources} }) {
      my $source_path = $manifest->{sources}{$source_id}{path} // '';
      my @chapters = grep {
        $_->{namespace} eq 'content'
          && $_->{kind} eq 'chapter'
          && $_->{source} eq $source_path
      } values %$records;
      _fail("edition source '$source_id' in $manifest_path must resolve to one persistently identified chapter")
        if @chapters != 1;
    }
    for my $structure_name (sort keys %{ $manifest->{structures} }) {
      my %selected;
      my $structure = $manifest->{structures}{$structure_name};
      for my $item (@{ $structure->{chapters} // [] }) {
        my @source_ids = exists $item->{source}
          ? ($item->{source}) : @{ $item->{sources} // [] };
        for my $source_id (@source_ids) {
          _fail("edition structure '$structure_name' references unknown source '$source_id'")
            if !exists $manifest->{sources}{$source_id};
          _fail("edition structure '$structure_name' repeats source '$source_id'")
            if $selected{$source_id}++;
        }
      }
      for my $group (@{ $structure->{appendices} // [] }) {
        for my $source_id (@{ $group->{sources} // [] }) {
          _fail("edition structure '$structure_name' references unknown source '$source_id'")
            if !exists $manifest->{sources}{$source_id};
          _fail("edition structure '$structure_name' repeats source '$source_id'")
            if $selected{$source_id}++;
        }
      }
      _fail("edition structure '$structure_name' has no persistently identified sources")
        if !keys %selected;
    }
  }
}

sub validate_migrations {
  my ($policy) = @_;
  my (%from, %edges);
  for my $migration (@{ $policy->{migrations} }) {
    _fail('each identity migration must be an object') if ref($migration) ne 'HASH';
    my $namespace = $migration->{namespace} // '';
    my $old = $migration->{from} // '';
    my $new = $migration->{to};
    _fail("invalid migration namespace '$namespace'")
      if $namespace !~ /^(?:content|glossary|index|asset)$/;
    _fail('identity migration from must be a valid ID')
      if $old !~ /^[A-Za-z][A-Za-z0-9_.:-]*$/;
    _fail("identity '$namespace:$old' has more than one migration")
      if $from{"$namespace\0$old"}++;
    _fail("identity migration '$namespace:$old' needs a reason")
      if ($migration->{reason} // '') !~ /\S/;
    if (defined $new) {
      _fail("identity migration '$namespace:$old' has an invalid replacement")
        if $new !~ /^[A-Za-z][A-Za-z0-9_.:-]*$/ || $new eq $old;
      $edges{"$namespace\0$old"} = "$namespace\0$new";
    }
  }
  for my $start (keys %edges) {
    my (%seen, $cursor);
    $cursor = $start;
    while (exists $edges{$cursor}) {
      _fail('identity migrations contain a cycle') if $seen{$cursor}++;
      $cursor = $edges{$cursor};
    }
  }
}

1;
