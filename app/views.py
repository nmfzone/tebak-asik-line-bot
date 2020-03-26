import json
import logging
import pydash
import re
from common.views import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Q
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    JoinEvent, SourceGroup, SourceRoom, SourceUser,
    TemplateSendMessage, ButtonsTemplate, URIAction
)
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (
    Player,
    Question
)
from .utils import (
    BOT_NAME, BOT_ID, BOT_CHANNEL_SECRET,
    BOT_CHANNEL_ACCESS_TOKEN, get_cache_prefix,
    get_player_identity, get_participant_identity
)

logger = logging.getLogger('django')

handler = WebhookHandler(BOT_CHANNEL_SECRET)
line_bot_api = LineBotApi(BOT_CHANNEL_ACCESS_TOKEN)


class IndexView(TemplateView):
    template_name = 'app:index.html'
    page_title = 'Line Bot'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'app:dashboard.html'
    page_title = 'Dashboard'


class LineBotApiView(APIView):
    def post(self, request):
        signature = request.META.get('HTTP_X_LINE_SIGNATURE')

        body = request.body.decode('utf-8')

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            logger.debug("Invalid signature. Please check your channel access token/channel secret.")
            return Response({
                'message': 'Failed'
            }, 400)

        return Response({
            'message': 'OK'
        })


@handler.add(MessageEvent, TextMessage)
def handle_message(event):
    # CONFIG
    max_question = 10
    #################################

    text = event.message.text

    if event.reply_token == '00000000000000000000000000000000':
        # Line trying to verify the Webhook
        return

    cache_prefix = get_cache_prefix(event)
    player_identity = get_player_identity(event)
    participant_identity = get_participant_identity(event)

    is_game_started = cache.get(cache_prefix + '.is_started', False)
    last_question = cache.get(cache_prefix + '.last_question', 1)
    remaining_time = cache.get(cache_prefix + '.remaining_time', False)
    participants = json.loads(cache.get(cache_prefix + '.participants', '[]'))
    current_question = json.loads(cache.get(cache_prefix + '.current_question', '{}'))
    current_standings = json.loads(cache.get(cache_prefix + '.current_standings', '[]'))
    standings = json.loads(cache.get(cache_prefix + '.standings', '[]'))
    player = cache.get(cache_prefix + '.player', False)

    if not player:
        player = Player.objects.filter(key=player_identity).first()

        if not player:
            player = Player.objects.create(
                key=player_identity
            )

        player = {
            'id': player.id,
            'key': player.key
        }

        cache.set(cache_prefix + '.player', json.dumps(player), None)
    else:
        player = json.loads(player)

    participant = cache.get('user_profiles.' + participant_identity)

    if not participant:
        try:
            line_profile = line_bot_api.get_profile(participant_identity)
            participant = {
                'user_id': line_profile.user_id,
                'display_name': line_profile.display_name
            }
            cache.set('user_profiles.' + participant_identity, json.dumps(participant))
        except LineBotApiError:
            # It seems participant not add bot as friend.
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(
                        'Yahh, kamu gak bisa ikutan main.\n\n' +
                        'Kamu belum add Bot %s jadi teman. ' % BOT_NAME +
                        'Add dulu dong Bot, biar kamu bisa ikutan main.'
                    ),
                    TemplateSendMessage(
                        alt_text='Tambah sebagai teman',
                        template=ButtonsTemplate(
                            # thumbnail_image_url='https://example.com/image.jpg',
                            title=BOT_NAME,
                            text='Tekan tombol di bawah ini untuk menambahkan bot sbg teman',
                            actions=[
                                URIAction('Tambahkan Teman', 'line://ti/p/@%s' % BOT_ID)
                            ]
                        )
                    )
                ]
            )
            return
    else:
        participant = json.loads(participant)

    process_text = False

    if text[0] == '/':
        if text == '/menu':
            output = '[Menu Permainan]\n\n'\
                '/join => Untuk berpartisipasi dalam permainan.\n\n'\
                '/mulai => Untuk memulai permainan.\n\n'\
                '/skip => Untuk skip pertanyaan (pertanyaan berikutnya).\n\n'\
                '/ulang => Untuk mengulangi permainan.\n\n'\
                '/klasemen => Untuk menampilkan klasemen permainan.\n\n'\
                '/identitas => Untuk mendapatkan ID Permainan.\n\n'

            if isinstance(event.source, SourceUser):
                output += '/tambah-pertanyaan => Untuk menambahkan pertanyaan ke sebuah permainan.\n\n'

            output += '/menu => Untuk memunculkan menu permainan ini.\n\n'\
                '/reset-paksa => Untuk mereset paksa bot (riwayat permainan akan hilang).\n\n'\
                '/tentang => Untuk melihat kontak creator.\n\n'\
                '/keluar => Untuk mengeluarkan bot.'

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(output)
            )
        elif text == '/tentang':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    ('[Creator Bot %s]\n\n' % BOT_NAME) +
                    'Jika anda menemukan bug, ingin mengirimkan ide, dan lain-lain, silahkan kontak ' +
                    'creator di line://ti/p/@ajf4387b\n\n' +
                    'Copyright @2020 nmflabs'
                )
            )
        elif text == '/identitas':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('ID Permainan: %s' % player_identity)
            )
        elif text == '/keluar':
            fresh_data(event)
            exit_text = 'Selamat tinggal semuanya. Kapan-kapan invite lagi yaa :*'

            if isinstance(event.source, SourceGroup):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(exit_text)
                )
                line_bot_api.leave_group(event.source.group_id)
            elif isinstance(event.source, SourceRoom):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(exit_text)
                )
                line_bot_api.leave_room(event.source.room_id)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Bot tidak bisa keluar otomatis. Silahkan unfriend Bot ini :(')
                )
        elif text == '/mulai':
            if is_game_started:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Permainan sudah dimulai.')
                )

                return
            elif len(participants) == 0:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Tidak bisa memulai permainan. Belum ada peserta.')
                )

                return

            cache.set(cache_prefix + '.is_started', True, None)

            question = get_next_question(event, player['id'])

            if not question:
                fresh_data(event)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Mohon maaf, belum ada pertanyaan. Silahkan coba lain waktu :(')
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token, [
                        TextSendMessage('Permainan dimulai.'),
                        question
                    ]
                )
        elif text == '/join':
            if is_game_started:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Permainan sudah dimulai.')
                )
                return

            idx = pydash.find_index(participants, lambda s: s['id'] == participant['user_id'])

            if idx != -1:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('%s telah tergabung dalam permainan.' % participant['display_name'])
                )
                return

            participants.append({
                'id': participant['user_id'],
                'name': participant['display_name']
            })
            cache.set(cache_prefix + '.participants', json.dumps(participants), None)
            show_participants(event, participants)
        elif text == '/klasemen':
            output = 'Klasemen\n'
            if len(standings) == 0:
                output += '\nKlasemen masih kosong.'
            else:
                for index, _participant in enumerate(standings):
                    output += '\n%s. %s (%s poin)' % (index + 1, _participant['name'], _participant['points'])

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(output)
            )
        elif text == '/skip':
            process_text = True
        elif text == '/ulang':
            # Ulangi permainan pada sesi ini
            if not is_game_started:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Permainan belum dimulai.')
                )
                return

            cache.delete(cache_prefix + '.last_question')
            cache.delete(cache_prefix + '.remaining_time')
            cache.delete(cache_prefix + '.current_question')
            cache.delete(cache_prefix + '.current_standings')

            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage('Permainan diulang.'),
                    get_next_question(event, player['id'], True)
                ]
            )
        elif text == '/reset-paksa':
            fresh_data(event)
            cache.delete(cache_prefix + '.standings')

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('Bot behasil di reset paksa.')
            )
        else:
            if text.startswith('/tambah-pertanyaan'):
                if not isinstance(event.source, SourceUser):
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage('Perintah tidak tersedia.')
                    )
                    return

                errors_text = [
                    '- Total skor harus 100',
                    '- Panjang pertanyaan minimal 20 dan maksimal 100 karakter',
                    '- Panjang jawaban minimal 3 dan maksimal 25 karakter',
                    '- Jumlah jawaban minimal 1 dan maksimal 10',
                    '- Pertanyaan tidak boleh mengandung karakter %s' % "';'",
                    '- Jawaban tidak boleh mengandung karakter %s, %s, %s, %s' % ("';'", "','", "'('", "')'")
                ]

                if text == '/tambah-pertanyaan':
                    output = 'Anda dapat menambahkan pertanyaan ke dalam Permainan lain.\n'\
                        'Silahkan ulangi perintah dengan menuliskan pertanyaan sesuai format berikut:\n\n'\
                        '/tambah-pertanyaan ID_PERMAINAN;PERTANYAAN;JAWABAN (Skor),JAWABAN (Skor),....\n\n'\
                        'Keterangan:'

                    for error_text in errors_text:
                        output += '\n%s' % error_text

                    line_bot_api.reply_message(
                        event.reply_token, [
                            TextSendMessage(output),
                            TextSendMessage(
                                'Contoh:\n' +
                                '/tambah-pertanyaan g-U8f41v103t42f90ops6fgqr;' +
                                'Nama-nama hewan berawalan A?;' +
                                'Ayam (70),Anjing (10)'
                            )
                        ]
                    )
                else:
                    text = text.replace('/tambah-pertanyaan ', '')
                    data = text.split(';')
                    game_id = ''
                    question = ''
                    answers = []
                    errors = []

                    format_correct = True

                    if len(data) == 3:
                        try:
                            game_id = data[0].strip()
                            question = data[1].strip()
                            answers = data[2].split(',')

                            total = 0
                            for index, answer in enumerate(answers):
                                answer = answer.strip()
                                result = re.search(r'.* \(([^)]+)\)$', answer)
                                ans = pydash.replace_end(answer, ' (%s)' % result[1], '')
                                score = int(result[1])

                                if len(answer) < 3 or len(answer) > 25:
                                    errors.append(2)
                                    format_correct = False

                                answers[index] = [ans, score]
                                total += score

                            if total != 100:
                                errors.append(0)
                                format_correct = False

                            if len(answers) > 10:
                                errors.append(3)
                                format_correct = False

                            if len(question) > 100 or len(question) < 20:
                                errors.append(1)
                                format_correct = False
                        except:
                            errors.append(3)
                            errors.append(4)
                            errors.append(5)
                            format_correct = False

                        _player = Player.objects.filter(key=game_id).first()

                        if not _player:
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage('ID Permainan tidak ditemukan.')
                            )
                        elif format_correct:
                            Question.objects.create(
                                value=question,
                                answers=answers,
                                creator_id=player['id'],
                                for_player=_player
                            )

                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(
                                    'Anda berhasil menambahkan pertanyaan ke dalam ' +
                                    'Permainan dengan ID %s' % game_id
                                )
                            )
                        else:
                            output = 'Format tidak sesuai. Pastikan Anda menuliskan sesuai format.\n\n'\
                                'Kesalahan:'

                            errors = list(set(errors))

                            for error in errors:
                                output += '\n%s' % errors_text[error]

                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(output)
                            )
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage('Format tidak sesuai.')
                        )
                return

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('Perintah tidak tersedia.')
            )

    if process_text or text[0] != '/':
        text = text.strip()
        line_messanges = []

        if text == '/skip':
            if not is_game_started:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('Permainan belum dimulai. Ketik /mulai untuk memulai permainan.')
                )
                return

            line_messanges.append(TextSendMessage('Masa gitu aja udah nyerah :('))

        if not is_game_started:
            fresh_data(event)
            return
        else:
            answers = current_question['answers']

            if text != '/skip':
                if remaining_time:
                    answer_id = -1
                    correct_answer = False
                    score = 0

                    for index, answer in enumerate(answers):
                        if answer[0].lower() == text:
                            correct_answer = True
                            answer_id = index
                            score = answer[1]
                            break

                    if correct_answer:
                        current_standings.append({
                            'id': participant['user_id'],
                            'name': participant['display_name'],
                            'answer_id': answer_id,
                            'score': score
                        })

                        cache.set(cache_prefix + '.current_standings', json.dumps(current_standings), None)
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage('"%s" tidak ada dalam daftar jawaban.' % text)
                        )
                        return
                else:
                    line_messanges.append(TextSendMessage('Waktu habis!'))

            output = '%sPertanyaan ke %s dari %s.\n\n' % (
                '(Skip) ' if text == '/skip' else '',
                last_question,
                max_question
            )
            output += current_question['text'] + '\n'
            for index, answer in enumerate(answers):
                idx = pydash.find_index(current_standings, lambda s: s['answer_id'] == index)

                if idx != -1:
                    output += '\n%s. %s (%s) - %s' % (
                        index + 1,
                        answer[0],
                        answer[1],
                        current_standings[idx]['name']
                    )
                else:
                    output += '\n%s. ____________' % (index + 1)

            line_messanges.append(TextSendMessage(output))

            if (
                text == '/skip' or
                len(current_standings) == len(answers) or
                (last_question + 1) == max_question or
                not remaining_time
            ):
                for _participant in participants:
                    total_score = 0
                    for cs in current_standings:
                        if cs['id'] == _participant['id']:
                            total_score += cs['score']
                    _participant['total_score'] = total_score

                participants.sort(key=lambda p: p['total_score'], reverse=True)
                output = 'Daftar Pemain\n'
                for index, _participant in enumerate(participants):
                    output += '\n%s. %s (%s)' % (index + 1, _participant['name'], _participant['total_score'])

                line_messanges.append(TextSendMessage(output))

                cache.set(cache_prefix + '.participants', json.dumps(participants), None)

                question = get_next_question(event, player['id'])

                if question:
                    line_messanges.append(question)
                else:
                    line_messanges.append(TextSendMessage('Pertandingan berakhir!'))
                    if participants[0]['total_score'] == 0:
                        output = 'Pemenang\n\nTidak ada pemenang.'
                    else:
                        output = 'Pemenang\n'
                        points = [3, 1]
                        for index, _participant in enumerate(participants):
                            if _participant['total_score'] == 0:
                                break

                            point = points[index]
                            output += '\n%s. %s (+%s poin)' % (index + 1, _participant['name'], point)

                            idx = pydash.find_index(standings, lambda s: s['id'] == _participant['id'])
                            if idx != -1:
                                standings[idx]['points'] += point
                            else:
                                standings.append({
                                    'id': _participant['id'],
                                    'name': _participant['name'],
                                    'points': point
                                })

                            if index == len(points) - 1:
                                break

                        standings.sort(key=lambda s: s['points'], reverse=True)
                        cache.set(cache_prefix + '.standings', json.dumps(standings), None)

                    line_messanges.append(TextSendMessage(output))

                    fresh_data(event)

        line_bot_api.reply_message(
            event.reply_token,
            line_messanges
        )


@handler.add(JoinEvent)
def handle_join(event):
    logger.debug('--- Bot Joining ---', event)
    fresh_data(event)

    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage('Halo, salam kenal! Perkenalkan, saya [Bot %s].' % BOT_NAME),
            TextSendMessage(
                'Untuk memulai permainan, silahkan ketik /mulai. Untuk melihat menu permainan, silahkan ketik /menu.'
            ),
            TextSendMessage('Selamat bermain.')
        ]
    )


def get_next_question(event, player_id, retry=False):
    max_question = 10  # change next time
    max_question_has_creator = 5
    time_per_question = 60  # seconds

    cache_prefix = get_cache_prefix(event)
    last_question = int(cache.get(cache_prefix + '.last_question', 0))
    used_questions = json.loads(cache.get(cache_prefix + '.used_questions', '[]'))

    qs = Question.objects.exclude(pk__in=used_questions)

    question = qs.filter(Q(for_player=None) | Q(for_player_id=player_id)).order_by('?').first()

    if question and question.for_player_id is not None:
        questions_has_creator = json.loads(cache.get(cache_prefix + '.questions_has_creator', '[]'))

        if len(questions_has_creator) >= max_question_has_creator:
            question = qs.filter(for_player=None).order_by('?').first()
        else:
            questions_has_creator.append(question.id)
            cache.set(cache_prefix + '.questions_has_creator', json.dumps(questions_has_creator), None)

    if not question:
        if retry:
            question = Question.objects.order_by('?').first()

        if not question:
            return

    cache.set(cache_prefix + '.last_question', last_question + 1, None)
    cache.set(cache_prefix + '.remaining_time', True, time_per_question)

    cache.set(cache_prefix + '.current_question', json.dumps({
        'text': question.value,
        'answers': question.answers
    }), None)

    cache.set(cache_prefix + '.current_standings', json.dumps([]), None)

    used_questions.append(question.id)
    cache.set(cache_prefix + '.used_questions', json.dumps(used_questions), None)

    output = question.value + '\n'
    for index, answer in enumerate(question.answers):
        output += '\n%s. ____________' % (index + 1)

    return TextSendMessage('Pertanyaan ke %s dari %s.\n\n%s' % (last_question+1, max_question, output))


def show_participants(event, participants):
    output = 'Daftar Pemain\n'
    for index, _participant in enumerate(participants):
        output += '\n%s. %s' % (index + 1, _participant['name'])

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(output)
    )


def fresh_data(event):
    logger.debug('--- Refreshing data ---', event)
    cache_prefix = get_cache_prefix(event)

    cache.delete(cache_prefix + '.is_started')
    cache.delete(cache_prefix + '.last_question')
    cache.delete(cache_prefix + '.remaining_time')
    cache.delete(cache_prefix + '.used_questions')
    cache.delete(cache_prefix + '.current_question')
    cache.delete(cache_prefix + '.participants')
    cache.delete(cache_prefix + '.current_standings')
    cache.delete(cache_prefix + '.questions_has_creator')
