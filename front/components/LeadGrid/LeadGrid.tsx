import { Container, Grid, SimpleGrid, Skeleton, Text, rem } from '@mantine/core';

const PRIMARY_COL_HEIGHT = rem(300);

export function LeadGrid() {
  const SECONDARY_COL_HEIGHT = `calc(${PRIMARY_COL_HEIGHT} / 2 - var(--mantine-spacing-md) / 2)`;

  return (
    <Container my="md">
        <Grid gutter="md">
          <Grid.Col>
            <Skeleton height={SECONDARY_COL_HEIGHT} radius="md" animate={false} />
            <Text>Colocar os links</Text>
          </Grid.Col>
          <Grid.Col>
            <Skeleton height={SECONDARY_COL_HEIGHT} radius="md" animate={false} />
            <Text>Botão de começar e de parar e os status</Text>
          </Grid.Col>
          <Grid.Col span={6}>
            <Skeleton height={SECONDARY_COL_HEIGHT} radius="md" animate={false} />
            <Text>Logs</Text>
          </Grid.Col>
          <Grid.Col span={6}>
            <Skeleton height={SECONDARY_COL_HEIGHT} radius="md" animate={false} />
            <Text>Erros</Text>
          </Grid.Col>
        </Grid>
    </Container>
  );
}
